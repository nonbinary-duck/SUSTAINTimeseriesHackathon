import pandas as pd

# Load the CSV
df = pd.read_csv("merged_data_completerows.csv")

# Keep only yield rows
yield_df = df[df["Element"] == "Yield"]

# Average of all yield values
avg_yield = yield_df["Value"].mean()

print(f"Average yield value: {avg_yield:.2f}")