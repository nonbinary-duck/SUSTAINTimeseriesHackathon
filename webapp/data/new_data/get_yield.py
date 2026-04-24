import pandas as pd
import re

def extract_crop_yields(input_file, output_file):
    # Mapping table numbers to human-readable names
    CROP_MAP = {
        "7_1": "Cereals",
        "7_2": "Wheat",
        "7_3": "Barley",
        "7_4": "Oats",
        "7_5": "Oilseed rape",
        "7_6": "Sugar beet",
        "7_7": "Protein crops",
        "7_8": "Fresh vegetables",
        "7_9": "Plants and flowers",
        "7_10": "Potatoes",
        "7_11": "Fresh fruit",
        "7_12": "Linseed"
    }

    print(f"Loading {input_file}...")
    try:
        all_sheets = pd.read_excel(input_file, sheet_name=None, engine='odf')
    except Exception as e:
        print(f"Error loading file: {e}")
        return

    final_data = []
    year_pattern = re.compile(r'^(19|20)\d{2}')

    for sheet_name, df in all_sheets.items():
        # Skip meta sheets
        if any(x in sheet_name.lower() for x in ['contents', 'notes', 'cover', 'toc']):
            continue
            
        # 1. Determine Crop Name using the Map
        table_id_match = re.search(r'7_\d+', sheet_name)
        if table_id_match:
            table_id = table_id_match.group(0)
            crop_name = CROP_MAP.get(table_id, table_id)
        else:
            crop_name = sheet_name.replace('Table_', '').replace('_', ' ')

        print(f"Processing {sheet_name} -> {crop_name}")

        # 2. Locate row indices
        yield_row_idx = None
        area_row_idx = None
        volume_row_idx = None
        header_row_idx = None

        for idx, row in df.iterrows():
            label = str(row.iloc[0]).lower().strip()
            
            # Find the header row by looking for year patterns
            if header_row_idx is None:
                row_str_values = [str(v) for v in row.values]
                if any(year_pattern.match(v) for v in row_str_values):
                    header_row_idx = idx

            if 'yield' in label:
                yield_row_idx = idx
            elif label.startswith('area ('):
                area_row_idx = idx
            elif 'volume of harvested production' in label:
                volume_row_idx = idx

        if header_row_idx is None:
            continue

        # 3. Extract and Transform Values
        years = df.iloc[header_row_idx]
        
        for i in range(1, len(years)):
            year_raw = str(years.iloc[i])
            year_match = year_pattern.match(year_raw)
            
            if year_match:
                year = year_match.group(0)
                yield_val = None
                
                # Logic: Use Yield row if available, otherwise calculate Volume / Area
                if yield_row_idx is not None:
                    yield_val = str(df.iloc[yield_row_idx, i])
                elif area_row_idx is not None and volume_row_idx is not None:
                    try:
                        area = re.sub(r'[^\d.]', '', str(df.iloc[area_row_idx, i]))
                        vol = re.sub(r'[^\d.]', '', str(df.iloc[volume_row_idx, i]))
                        if area and vol:
                            # Calculation result is in tonnes/ha
                            yield_val = float(vol) / float(area)
                    except (ValueError, ZeroDivisionError):
                        yield_val = None

                # Clean, Convert to Float, and multiply by 1000 for kg/ha
                if yield_val is not None and str(yield_val) not in ['[x]', 'nan', 'None', '']:
                    try:
                        # Strip footnote markers like [Note 1]
                        clean_str = re.sub(r'\[.*?\]', '', str(yield_val))
                        # Keep only numbers and decimal point
                        clean_str = re.sub(r'[^\d.]', '', clean_str)
                        
                        if clean_str:
                            # Convert tonnes/ha to kg/ha
                            yield_kg_ha = float(clean_str) * 1000
                            
                            final_data.append({
                                'Crop': crop_name,
                                'Year': int(year),
                                'Yield_kg_per_ha': round(yield_kg_ha, 2)
                            })
                    except ValueError:
                        continue

    if final_data:
        output_df = pd.DataFrame(final_data)
        output_df = output_df.drop_duplicates().sort_values(['Crop', 'Year'])
        output_df.to_csv(output_file, index=False)
        print(f"\nSuccess! Saved {len(output_df)} data points to {output_file}")
    else:
        print("\nNo data extracted.")

if __name__ == "__main__":
    extract_crop_yields('AUK-chapter7-20250710.ods', 'uk_crop_yields_kg.csv')