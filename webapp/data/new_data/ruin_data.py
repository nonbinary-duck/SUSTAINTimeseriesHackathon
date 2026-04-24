import pandas as pd
import os

def calculate_yearly_averages_all_fields(input_csv):
    if not os.path.exists(input_csv):
        print(f"Error: {input_csv} not found. Please run the scraper first.")
        return

    # 1. Load the dataset
    df = pd.read_csv(input_csv)

    # 2. Define the columns we want to average
    # We exclude station names, lat, lon, and month
    data_cols = ['tmax_degC', 'tmin_degC', 'af_days', 'rain_mm', 'sun_hours']
    
    # 3. Ensure all data columns are numeric
    # 'coerce' turns 'NaN' strings or errors into actual numeric NaN objects
    for col in data_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # 4. Group by Year and calculate the Mean
    # numeric_only=True ensures we don't try to average the station names
    # .mean() automatically skips NaN values (the "don't sully" requirement)
    yearly_df = df.groupby('year')[data_cols].mean().reset_index()

    # 5. Clean up the output
    # Rounding to 2 decimal places for a clean CSV
    yearly_df = yearly_df.round(2)
    
    # 6. Save and Display
    output_file = "yearly_uk_weather_averages_all_fields.csv"
    yearly_df.to_csv(output_file, index=False)
    
    print(f"Success! Yearly averages for all fields saved to: {output_file}")
    print("\nFirst 10 years of averaged data:")
    print(yearly_df.head(10).to_string(index=False))

if __name__ == "__main__":
    calculate_yearly_averages_all_fields("met_office_all_stations.csv")