import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

def load_csv_safely(csv_path="results_v1.csv"):
    lines = Path(csv_path).read_text(encoding="utf-8", errors="replace").splitlines()
    rows = []
    for line in lines[1:]:
        if not line.strip(): 
            continue
        parts = line.split(",")
        if len(parts) >= 6:
            algo, n, it, tns = parts[0], int(parts[1]), int(parts[2]), int(parts[3])
            tms = float(f"{parts[4]}.{parts[5]}")
        elif len(parts) == 5:
            algo, n, it, tns, tms = parts[0], int(parts[1]), int(parts[2]), int(parts[3]), float(parts[4])
        else:
            continue
        rows.append([algo, n, it, tns, tms])
    return pd.DataFrame(rows, columns=["algorithm", "n", "iteration", "time_ns", "time_ms"])

def generate_v1_plots():
    df = load_csv_safely("results_v1.csv")
    
    # Medians by algorithm and n
    agg = df.groupby(["algorithm", "n"], as_index=False)["time_ns"].median()
    piv = agg.pivot(index="n", columns="algorithm", values="time_ns").sort_index()
    
    n_vals = piv.index.values.astype(float)
    log2_n = np.log2(np.clip(n_vals, 2, None))
    
    plt.rcParams.update({'figure.figsize': (10, 5), 'font.size': 10})

    # 1. Absolute times on a logarithmic scale to see the differences in magnitude
    plt.figure()
    for col in piv.columns:
        plt.plot(n_vals, piv[col] / 1e6, marker='o', label=col)
    plt.xlabel("Input Size (n)")
    plt.ylabel("Median Time (ms)")
    plt.yscale("log")
    plt.title("Variant 1: Absolute Execution Times (Log Y Scale)")
    plt.grid(True, which="both", linestyle=":", alpha=0.6)
    plt.legend()
    plt.tight_layout()
    plt.savefig("v1_raw_times.png", dpi=300)
    plt.close()

    # 2. Normalization for O(n): t / n
    plt.figure()
    for col in piv.columns:
        plt.plot(n_vals, piv[col] / n_vals, marker='s', label=col)
    plt.xlabel("Input Size (n)")
    plt.ylabel("Time / n (ns per element)")
    plt.xscale("log")
    plt.title("Normalization for O(n): t / n")
    plt.grid(True, which="both", linestyle=":", alpha=0.6)
    plt.legend()
    plt.tight_layout()
    plt.savefig("v1_norm_linear.png", dpi=300)
    plt.close()

    # 3. Normalization for O(n log n): t / (n · log2(n))
    plt.figure()
    for col in piv.columns:
        plt.plot(n_vals, piv[col] / (n_vals * log2_n), marker='^', label=col)
    plt.xlabel("Input Size (n)")
    plt.ylabel("Time / (n · log2(n))")
    plt.xscale("log")
    plt.title("Normalization for O(n log n): t / (n · log2(n))")
    plt.grid(True, which="both", linestyle=":", alpha=0.6)
    plt.legend()
    plt.tight_layout()
    plt.savefig("v1_norm_nlogn.png", dpi=300)
    plt.close()

    print("Plots generated successfully!")

if __name__ == "__main__":
    generate_v1_plots()