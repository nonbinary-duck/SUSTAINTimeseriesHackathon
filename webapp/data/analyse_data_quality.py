import pandas as pd
import numpy as np

def analyze_data_quality():
    print("=== Loading Datasets ===")
    try:
        # Added low_memory=False to handle the DtypeWarning
        merged_df = pd.read_csv('merged_data.csv', low_memory=False)
        rain_df = pd.read_csv('rainfall.csv', low_memory=False)
        temp_df = pd.read_csv('temp.csv', low_memory=False) 
    except FileNotFoundError as e:
        print(f"Error: {e}. Please ensure files are in the same directory.")
        return

    # STRIP WHITESPACE FROM COLUMN NAMES to prevent KeyError
    merged_df.columns = merged_df.columns.str.strip()
    rain_df.columns = rain_df.columns.str.strip()
    temp_df.columns = temp_df.columns.str.strip()

    # Standardize column names for Temp dataframe
    if 'country' in temp_df.columns:
        temp_df = temp_df.rename(columns={'country': 'Area'})
    if 'year' in temp_df.columns:
        temp_df = temp_df.rename(columns={'year': 'Year'})

    print("\n=== Row Counts & Basic Info ===")
    print(f"Raw Merged Data: {len(merged_df)} rows")
    print(f"Rainfall Data: {len(rain_df)} rows")
    print(f"Temperature Data: {len(temp_df)} rows")

    print("\n=== Analyzing Missing Years ===")
    merged_years = set(merged_df['Year'].dropna().unique()) if 'Year' in merged_df.columns else set()
    rain_years = set(rain_df['Year'].dropna().unique()) if 'Year' in rain_df.columns else set()
    temp_years = set(temp_df['Year'].dropna().unique()) if 'Year' in temp_df.columns else set()

    expected_years = set(range(1985, 2014))
    
    print(f"Years missing in Merged: {sorted(expected_years - merged_years)}")
    print(f"Years missing in Rainfall: {sorted(expected_years - rain_years)}")
    print(f"Years missing in Temp: {sorted(expected_years - temp_years)}")

    print("\n=== Area/Country Coverage ===")
    if 'Area' in merged_df.columns and 'Area' in rain_df.columns and 'Area' in temp_df.columns:
        merged_areas = set(merged_df['Area'].dropna().unique())
        rain_areas = set(rain_df['Area'].dropna().unique())
        temp_areas = set(temp_df['Area'].dropna().unique())

        temp_not_in_rain = temp_areas - rain_areas
        
        print(f"Total unique countries in Merged: {len(merged_areas)}")
        print(f"Total unique countries in Rainfall: {len(rain_areas)}")
        print(f"Total unique countries in Temp: {len(temp_areas)}")
        print(f"Countries in Temp but missing in Rainfall: {len(temp_not_in_rain)}")
    else:
        print("Could not find 'Area' column. Available columns:")
        print(f"Merged: {merged_df.columns.tolist()}")
        print(f"Rain: {rain_df.columns.tolist()}")
        print(f"Temp: {temp_df.columns.tolist()}")

    print("\n=== Investigating the Rainfall String Issue ===")
    # Find out exactly what text is breaking the rainfall column
    if 'average_rain_fall_mm_per_year' in rain_df.columns:
        if rain_df['average_rain_fall_mm_per_year'].dtype == object:
            bad_rain_values = rain_df[pd.to_numeric(rain_df['average_rain_fall_mm_per_year'], errors='coerce').isna()]
            unique_bad_values = bad_rain_values['average_rain_fall_mm_per_year'].unique()
            print(f"Found non-numeric rainfall values: {unique_bad_values}")
            print(f"Number of rows with bad rainfall data: {len(bad_rain_values)}")
        else:
            print("Rainfall column is numeric.")

if __name__ == "__main__":
    analyze_data_quality()