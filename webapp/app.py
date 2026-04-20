import os
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import pandas as pd
import numpy as np
import joblib

app = Flask(__name__)
CORS(app)

# -----------------------------------------------
# LOAD MODEL + DATA AT STARTUP
# -----------------------------------------------
model   = joblib.load("model/xgb_model.pkl")
le_area = joblib.load("model/le_area.pkl")
le_crop = joblib.load("model/le_crop.pkl")

df = pd.read_csv("data/merged_data_completerows.csv")
df["average_rain_fall_mm_per_year"] = pd.to_numeric(
    df["average_rain_fall_mm_per_year"], errors="coerce"
)
df = df.dropna(subset=["average_rain_fall_mm_per_year"])
df = df.groupby(["Year", "Area", "Item"], as_index=False).agg({
    "avg_temp": "mean",
    "average_rain_fall_mm_per_year": "mean",
    "Value": "mean"
})

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
    locations = sorted(df["Area"].unique().tolist())
    return jsonify(locations)

@app.route("/api/crops", methods=["GET"])
def get_crops():
    area = request.args.get("area", None)
    if area:
        crops = sorted(df[df["Area"] == area]["Item"].unique().tolist())
    else:
        crops = sorted(df["Item"].unique().tolist())
    return jsonify(crops)

@app.route("/api/chart-data", methods=["GET"])
def get_chart_data():
    area = request.args.get("area")
    crop = request.args.get("crop")
    if not area or not crop:
        return jsonify({"error": "area and crop are required"}), 400

    subset = df[(df["Area"] == area) & (df["Item"] == crop)].copy()
    subset = subset.reset_index(drop=True)

    if subset.empty:
        return jsonify({"error": f"No data for {area} / {crop}"}), 404

    if area not in le_area.classes_ or crop not in le_crop.classes_:
        return jsonify({"error": "Unknown area or crop"}), 400

    subset["Area_encoded"] = le_area.transform(subset["Area"])
    subset["Item_encoded"] = le_crop.transform(subset["Item"])

    features = ["Year", "Area_encoded", "Item_encoded",
                "avg_temp", "average_rain_fall_mm_per_year"]
    preds = model.predict(subset[features])

    result = []
    for idx, row in subset.iterrows():
        result.append({
            "year":      int(row["Year"]),
            "actual":    round(float(row["Value"]), 1),
            "predicted": round(float(preds[idx]), 1),
            "avg_temp":  round(float(row["avg_temp"]), 2),
            "rainfall":  round(float(row["average_rain_fall_mm_per_year"]), 1)
        })

    result.sort(key=lambda x: x["year"])
    return jsonify(result)

@app.route("/api/feature-importance", methods=["GET"])
def get_feature_importance():
    labels = ["Year", "Country", "Crop Type", "Avg Temp", "Rainfall"]
    data = [
        {"feature": label, "importance": round(float(imp), 4)}
        for label, imp in zip(labels, model.feature_importances_)
    ]
    data.sort(key=lambda x: x["importance"], reverse=True)
    return jsonify(data)

if __name__ == "__main__":
    # Disable debug mode if running inside the CI pipeline
    is_ci = os.environ.get("CI_AUTO_BUILD") == "true"
    app.run(host="0.0.0.0", port=5001, debug=not is_ci)