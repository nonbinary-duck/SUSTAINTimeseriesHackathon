import pandas as pd
import numpy as np
from xgboost import XGBRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_absolute_error, r2_score
import matplotlib.pyplot as plt
import joblib

# -----------------------------------------------
# LOAD & MERGE DATA
# -----------------------------------------------
# Load weather and yield data
weather_df = pd.read_csv("data/new_data/yearly_uk_weather_averages_all_fields.csv")
yield_df = pd.read_csv("data/new_data/uk_crop_yields_kg.csv")

# Ensure the year column has the same name in both DataFrames
weather_df = weather_df.rename(columns={"year": "Year"})

# Merge the datasets on 'Year'
df = pd.merge(yield_df, weather_df, on="Year", how="inner")

# -----------------------------------------------
# CLEAN DATA
# -----------------------------------------------
# Ensure numeric columns are properly formatted and drop missing values 
# (Note: sun_hours are missing in older years, but since crop yields 
# only go back to 1980, dropping NaNs after the merge is perfectly safe).
df = df.dropna()

print(f"Clean dataset shape: {df.shape}")
print(df.head())

# -----------------------------------------------
# ENCODE CATEGORICAL VARIABLES
# -----------------------------------------------
# Only Crop needs encoding since Area is always UK
le_crop = LabelEncoder()
df["Crop_encoded"] = le_crop.fit_transform(df["Crop"])

# -----------------------------------------------
# FEATURES & TARGET
# -----------------------------------------------
features = [
    "Year", 
    "Crop_encoded", 
    "tmax_degC", 
    "tmin_degC", 
    "af_days", 
    "rain_mm", 
    "sun_hours"
]

target = "Yield_kg_per_ha"  # yield in kg/ha

# -----------------------------------------------
# TIME-BASED TRAIN/TEST SPLIT
# Train on < 2008, test on 2008 onwards
# -----------------------------------------------
SPLIT_YEAR = 2008

train_df = df[df["Year"] < SPLIT_YEAR]
test_df  = df[df["Year"] >= SPLIT_YEAR]

X_train = train_df[features]
y_train = train_df[target]

X_test  = test_df[features]
y_test  = test_df[target]

print(f"\nTraining on {len(X_train)} rows (up to {SPLIT_YEAR - 1})")
print(f"Testing on  {len(X_test)} rows ({SPLIT_YEAR} onwards)")

# -----------------------------------------------
# TRAIN XGBOOST
# -----------------------------------------------
model = XGBRegressor(
    n_estimators=300,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    n_jobs=-1
)

model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    verbose=50  # print every 50 rounds
)

# -----------------------------------------------
# EVALUATE
# -----------------------------------------------
y_pred = model.predict(X_test)

mae = mean_absolute_error(y_test, y_pred)
r2  = r2_score(y_test, y_pred)

print(f"\n=== MODEL PERFORMANCE ===")
print(f"MAE : {mae:,.0f} kg/ha")
print(f"R²  : {r2:.4f}")

# -----------------------------------------------
# FEATURE IMPORTANCE
# -----------------------------------------------
importance = pd.DataFrame({
    "feature": features,
    "importance": model.feature_importances_
}).sort_values("importance", ascending=False)

print("\n=== FEATURE IMPORTANCE ===")
print(importance)

# -----------------------------------------------
# SAVE MODEL & ENCODERS (with new prefixes)
# -----------------------------------------------
joblib.dump(model, "model/uk_xgb_model.pkl")
joblib.dump(le_crop, "model/uk_le_crop.pkl")

print("\nModels saved to model/ folder with 'uk_' prefix.")