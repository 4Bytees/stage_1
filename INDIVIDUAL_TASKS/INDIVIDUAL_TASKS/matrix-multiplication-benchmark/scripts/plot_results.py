import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Load benchmark results
csv_path = Path("data/raw/results.csv")
if not csv_path.exists():
    print(f"Error: File not found at {csv_path}")
    exit(1)

df = pd.read_csv(csv_path)

# Filter successful executions only
df_ok = df[df["status"] == "ok"].copy()

# Group by language and matrix size (n), calculating median time and memory
summary = df_ok.groupby(["lang", "n"]).agg({
    "time_s": "median",
    "peak_mem_mb": "median"
}).reset_index()

plots_dir = Path("data/plots")
plots_dir.mkdir(parents=True, exist_ok=True)

# 1. Execution Time vs. Matrix Size (n) Plot
plt.figure(figsize=(9, 5))
for lang in summary["lang"].unique():
    sub = summary[summary["lang"] == lang]
    plt.plot(sub["n"], sub["time_s"], marker="o", linewidth=2, label=lang.upper())

plt.title("Matrix Multiplication O(n³) - Execution Time")
plt.xlabel("Matrix Size (n)")
plt.ylabel("Median Time (seconds)")
plt.yscale("log")  # Logarithmic scale to compare C vs. Java vs. Python
plt.grid(True, linestyle="--", alpha=0.6)
plt.legend()
plt.tight_layout()
time_plot = plots_dir / "matrix_time_comparison.png"
plt.savefig(time_plot, dpi=300)
plt.close()

# 2. Peak RAM Memory Usage vs. Matrix Size (n) Plot
plt.figure(figsize=(9, 5))
for lang in summary["lang"].unique():
    sub = summary[summary["lang"] == lang]
    plt.plot(sub["n"], sub["peak_mem_mb"], marker="s", linewidth=2, label=lang.upper())

plt.title("Matrix Multiplication O(n³) - Peak Memory Usage")
plt.xlabel("Matrix Size (n)")
plt.ylabel("Peak Memory (MB)")
plt.grid(True, linestyle="--", alpha=0.6)
plt.legend()
plt.tight_layout()
mem_plot = plots_dir / "matrix_memory_comparison.png"
plt.savefig(mem_plot, dpi=300)
plt.close()

print(f"Plots successfully generated in {plots_dir}!")
print(f" - {time_plot.name}")
print(f" - {mem_plot.name}")