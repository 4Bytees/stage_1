import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

df = pd.read_csv("results_v3_comparison.csv")
piv = df.pivot(index="n", columns="algorithm", values="time_ns")

plt.figure(figsize=(10, 6))
for col in piv.columns:
    plt.plot(piv.index, piv[col], marker='o', linewidth=2, label=col)

plt.xscale("log")
plt.yscale("log")
plt.xlabel("Input Size n (Logarithmic Scale)")
plt.ylabel("Execution Time in ns (Logarithmic Scale)")
plt.title("Variant 3: Growth Rate Comparison (Log-Log Plot)")
plt.grid(True, which="both", linestyle=":", alpha=0.7)
plt.legend()
plt.tight_layout()
plt.savefig("v3_loglog_comparison.png", dpi=300)
print("Log-log plot saved as 'v3_loglog_comparison.png'")