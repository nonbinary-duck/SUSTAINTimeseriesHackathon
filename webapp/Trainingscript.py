import pandas as pd

import numpy as np

from xgboost import XGBRegressor

from sklearn.preprocessing import LabelEncoder

from sklearn.metrics import mean_absolute_error, r2_score

import matplotlib.pyplot as plt

# -----------------------------------------------

# LOAD & CLEAN

# -----------------------------------------------

df = pd.read_csv("data/merged_data_completerows.csv")


df = df.drop(columns=["Domain", "Element", "Unit"], errors="ignore")

# Handle ".." rainfall values (Bahamas etc.) - replace with NaN then drop

df["average_rain_fall_mm_per_year"] = pd.to_numeric(

    df["average_rain_fall_mm_per_year"], errors="coerce"

)

df = df.dropna()

# Remove duplicate rows (some countries have multiple temp stations per year)

# Average the temp across stations for the same country/year/crop combo

df = df.groupby(["Year", "Area", "Item"], as_index=False).agg({

    "avg_temp": "mean",

    "average_rain_fall_mm_per_year": "mean",

    "Value": "mean"

})

print(f"Clean dataset shape: {df.shape}")

print(df.head())

# -----------------------------------------------

# ENCODE CATEGORICAL VARIABLES

# -----------------------------------------------

le_area = LabelEncoder()

le_crop = LabelEncoder()

df["Area_encoded"] = le_area.fit_transform(df["Area"])

df["Item_encoded"] = le_crop.fit_transform(df["Item"])

# -----------------------------------------------

# FEATURES & TARGET

# -----------------------------------------------

features = ["Year", "Area_encoded", "Item_encoded", "avg_temp", "average_rain_fall_mm_per_year"]

target = "Value"  # yield in hg/ha

# -----------------------------------------------

# TIME-BASED TRAIN/TEST SPLIT

# Train on 1985-2008, test on 2009-2013

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

print(f"MAE : {mae:,.0f} hg/ha")

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

# SAVE MODEL & ENCODERS (so Flask can use them)

# -----------------------------------------------

import joblib

joblib.dump(model, "model/xgb_model.pkl")

joblib.dump(le_area, "model/le_area.pkl")

joblib.dump(le_crop, "model/le_crop.pkl")

print("\nModel saved to model/ folder")