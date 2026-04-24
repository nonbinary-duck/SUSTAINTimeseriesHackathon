import os
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import pandas as pd
import numpy as np
import joblib

app = Flask(__name__)
CORS(app)

# -----------------------------------------------
# LOAD GLOBAL MODEL + DATA AT STARTUP
# -----------------------------------------------
global_model   = joblib.load("model/xgb_model.pkl")
global_le_area = joblib.load("model/le_area.pkl")
global_le_crop = joblib.load("model/le_crop.pkl")

df_global = pd.read_csv("data/merged_data_completerows.csv")
df_global["average_rain_fall_mm_per_year"] = pd.to_numeric(
    df_global["average_rain_fall_mm_per_year"], errors="coerce"
)
df_global = df_global.dropna(subset=["average_rain_fall_mm_per_year"])
df_global = df_global.groupby(["Year", "Area", "Item"], as_index=False).agg({
    "avg_temp": "mean",
    "average_rain_fall_mm_per_year": "mean",
    "Value": "mean"
})

# -----------------------------------------------
# LOAD UK MODEL + DATA AT STARTUP
# -----------------------------------------------
uk_model   = joblib.load("model/uk_xgb_model.pkl")
uk_le_crop = joblib.load("model/uk_le_crop.pkl")

weather_df = pd.read_csv("data/new_data/yearly_uk_weather_averages_all_fields.csv")
weather_df = weather_df.rename(columns={"year": "Year"})
yield_df = pd.read_csv("data/new_data/uk_crop_yields_kg.csv")
df_uk = pd.merge(yield_df, weather_df, on="Year", how="inner").dropna()

# -----------------------------------------------
# SERVE FRONTEND
# -----------------------------------------------
@app.route("/")
def index():
    # Pass CI variables to Jinja
    return render_template(
        "index.html",
        show_ci=(os.environ.get("CI_AUTO_BUILD") == "true"),
        commit_id=os.environ.get("COMMIT_ID", "Unknown"),
        build_time=os.environ.get("BUILD_TIME", "Unknown")
    )

# -----------------------------------------------
# API ENDPOINTS
# -----------------------------------------------
@app.route("/api/locations", methods=["GET"])
def get_locations():
    dataset = request.args.get("dataset", "global")
    if dataset == "uk":
        return jsonify(["United Kingdom"])
    else:
        locations = sorted(df_global["Area"].unique().tolist())
        return jsonify(locations)

@app.route("/api/crops", methods=["GET"])
def get_crops():
    dataset = request.args.get("dataset", "global")
    area = request.args.get("area", None)
    
    if dataset == "uk":
        crops = sorted(df_uk["Crop"].unique().tolist())
    else:
        if area:
            crops = sorted(df_global[df_global["Area"] == area]["Item"].unique().tolist())
        else:
            crops = sorted(df_global["Item"].unique().tolist())
            
    return jsonify(crops)

@app.route("/api/chart-data", methods=["GET"])
def get_chart_data():
    dataset = request.args.get("dataset", "global")
    area = request.args.get("area")
    crop = request.args.get("crop")

    # ----- UK DATASET LOGIC -----
    if dataset == "uk":
        if not crop:
            return jsonify({"error": "crop is required"}), 400

        subset = df_uk[df_uk["Crop"] == crop].copy().reset_index(drop=True)
        if subset.empty:
            return jsonify({"error": f"No data for {crop} in the UK dataset"}), 404

        if crop not in uk_le_crop.classes_:
            return jsonify({"error": "Unknown crop"}), 400

        subset["Crop_encoded"] = uk_le_crop.transform(subset["Crop"])
        features = ["Year", "Crop_encoded", "tmax_degC", "tmin_degC", "af_days", "rain_mm", "sun_hours"]
        preds = uk_model.predict(subset[features])

        result = []
        for idx, row in subset.iterrows():
            result.append({
                "year":      int(row["Year"]),
                "actual":    round(float(row["Yield_kg_per_ha"]), 1),
                "predicted": round(float(preds[idx]), 1),
                # Average the max and min temps so the climate chart renders smoothly
                "avg_temp":  round(float((row["tmax_degC"] + row["tmin_degC"]) / 2), 2),
                "rainfall":  round(float(row["rain_mm"]), 1),
                "unit":      "kg/ha"
            })
        result.sort(key=lambda x: x["year"])
        return jsonify(result)

    # ----- GLOBAL DATASET LOGIC -----
    else:
        if not area or not crop:
            return jsonify({"error": "area and crop are required"}), 400

        subset = df_global[(df_global["Area"] == area) & (df_global["Item"] == crop)].copy().reset_index(drop=True)

        if subset.empty:
            return jsonify({"error": f"No data for {area} / {crop}"}), 404

        if area not in global_le_area.classes_ or crop not in global_le_crop.classes_:
            return jsonify({"error": "Unknown area or crop"}), 400

        subset["Area_encoded"] = global_le_area.transform(subset["Area"])
        subset["Item_encoded"] = global_le_crop.transform(subset["Item"])

        features = ["Year", "Area_encoded", "Item_encoded", "avg_temp", "average_rain_fall_mm_per_year"]
        preds = global_model.predict(subset[features])

        result = []
        for idx, row in subset.iterrows():
            result.append({
                "year":      int(row["Year"]),
                "actual":    round(float(row["Value"]), 1),
                "predicted": round(float(preds[idx]), 1),
                "avg_temp":  round(float(row["avg_temp"]), 2),
                "rainfall":  round(float(row["average_rain_fall_mm_per_year"]), 1),
                "unit":      "hg/ha"
            })

        result.sort(key=lambda x: x["year"])
        return jsonify(result)

@app.route("/api/feature-importance", methods=["GET"])
def get_feature_importance():
    dataset = request.args.get("dataset", "global")
    
    if dataset == "uk":
        labels = ["Year", "Crop Type", "Max Temp", "Min Temp", "Frost Days", "Rainfall", "Sun Hours"]
        importances = uk_model.feature_importances_
    else:
        labels = ["Year", "Country", "Crop Type", "Avg Temp", "Rainfall"]
        importances = global_model.feature_importances_

    data = [
        {"feature": label, "importance": round(float(imp), 4)}
        for label, imp in zip(labels, importances)
    ]
    data.sort(key=lambda x: x["importance"], reverse=True)
    return jsonify(data)

if __name__ == "__main__":
    is_ci = os.environ.get("CI_AUTO_BUILD") == "true"
    app.run(host="0.0.0.0", port=5001, debug=not is_ci)