import pandas as pd

# Load the CSV
df = pd.read_csv("merged_data_completerows.csv")

# Basic overview
print("\n=== Data Overview ===")
print(f"Rows: {len(df)}")
print(f"Columns: {len(df.columns)}")
print("\nColumns:")
print(df.columns.tolist())

print("\n=== First 5 Rows ===")
print(df.head())

print("\n=== Data Types ===")
print(df.dtypes)

print("\n=== Missing Values ===")
print(df.isnull().sum())

# Year analysis
print("\n=== Year Analysis ===")
unique_years = sorted(df["Year"].unique())
print(f"Number of unique years: {len(unique_years)}")
print("Years:")
print(unique_years)

print("\nRows per year:")
year_counts = df["Year"].value_counts().sort_index()
print(year_counts)

# 20% most recent years
n_years = len(unique_years)
test_years_count = round(n_years * 0.2)
test_years = unique_years[-test_years_count:]

print("\n=== Suggested Time-Based Split ===")
print(f"20% of {n_years} years ≈ {test_years_count} years")
print(f"Use these years for test/validation: {test_years}")
print(f"Train on years before {test_years[0]}")
print(f"Test/validation on years >= {test_years[0]}")

# Optional: count rows in train/test split
train_df = df[df["Year"] < test_years[0]]
test_df = df[df["Year"] >= test_years[0]]

print("\n=== Split Row Counts ===")
print(f"Train rows: {len(train_df)}")
print(f"Test/validation rows: {len(test_df)}")
print(f"Test percentage by rows: {len(test_df) / len(df) * 100:.2f}%")


# python3 year_frequency.py 

# === Data Overview ===
# Rows: 44135
# Columns: 9

# Columns:
# ['Year', 'Area', 'avg_temp', 'average_rain_fall_mm_per_year', 'Domain', 'Element', 'Item', 'Unit', 'Value']

# === First 5 Rows ===
#    Year         Area  avg_temp average_rain_fall_mm_per_year Domain Element         Item   Unit     Value
# 0  1985  Afghanistan     15.52                           327  Crops   Yield        Maize  hg/ha   16652.0
# 1  1985  Afghanistan     15.52                           327  Crops   Yield     Potatoes  hg/ha  140909.0
# 2  1985  Afghanistan     15.52                           327  Crops   Yield  Rice, paddy  hg/ha   22482.0
# 3  1985  Afghanistan     15.52                           327  Crops   Yield        Wheat  hg/ha   12277.0
# 4  1986  Afghanistan     14.71                           327  Crops   Yield        Maize  hg/ha   16875.0

# === Data Types ===
# Year                               int64
# Area                                 str
# avg_temp                         float64
# average_rain_fall_mm_per_year        str
# Domain                               str
# Element                              str
# Item                                 str
# Unit                                 str
# Value                            float64
# dtype: object

# === Missing Values ===
# Year                             0
# Area                             0
# avg_temp                         0
# average_rain_fall_mm_per_year    0
# Domain                           0
# Element                          0
# Item                             0
# Unit                             0
# Value                            0
# dtype: int64

# === Year Analysis ===
# Number of unique years: 27
# Years:
# [np.int64(1985), np.int64(1986), np.int64(1987), np.int64(1989), np.int64(1990), np.int64(1991), np.int64(1992), np.int64(1993), np.int64(1994), np.int64(1995), np.int64(1996), np.int64(1997), np.int64(1998), np.int64(1999), np.int64(2000), np.int64(2001), np.int64(2002), np.int64(2004), np.int64(2005), np.int64(2006), np.int64(2007), np.int64(2008), np.int64(2009), np.int64(2010), np.int64(2011), np.int64(2012), np.int64(2013)]

# Rows per year:
# Year
# 1985    1559
# 1986    1560
# 1987    1560
# 1989    1566
# 1990    1570
# 1991    1575
# 1992    1636
# 1993    1640
# 1994    1638
# 1995    1639
# 1996    1639
# 1997    1639
# 1998    1639
# 1999    1640
# 2000    1647
# 2001    1646
# 2002    1645
# 2004    1651
# 2005    1652
# 2006    1668
# 2007    1669
# 2008    1671
# 2009    1669
# 2010    1672
# 2011    1672
# 2012    1687
# 2013    1686
# Name: count, dtype: int64

# === Suggested Time-Based Split ===
# 20% of 27 years ≈ 5 years
# Use these years for test/validation: [np.int64(2009), np.int64(2010), np.int64(2011), np.int64(2012), np.int64(2013)]
# Train on years before 2009
# Test/validation on years >= 2009

# === Split Row Counts ===
# Train rows: 35749
# Test/validation rows: 8386
# Test percentage by rows: 19.00%