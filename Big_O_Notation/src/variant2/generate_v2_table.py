import pandas as pd

df = pd.read_csv("results_v2_limits.csv")
print("\n=== n_max TABLE BY ALGORITHM (BUDGET = 5 SECONDS) ===")
summary = []
for algo, group in df.groupby("algorithm"):
    max_valid = group[group["time_ms"] <= 5000]["n"].max()
    first_exceeded = group[group["time_ms"] > 5000]["n"].min()
    max_time = group["time_ms"].max()
    summary.append({
        "Algorithm": algo,
        "Practicable n_max (t <= 5s)": max_valid,
        "n that exceeds the budget": first_exceeded if pd.notna(first_exceeded) else "Not exceeded (RAM limit)",
        "Maximum recorded time (ms)": max_time
    })

res_df = pd.DataFrame(summary)
print(res_df.to_string(index=False))