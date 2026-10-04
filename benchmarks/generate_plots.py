import json
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
BENCHMARKS_DIR = BASE_DIR / "benchmarks"
JSON_FILE = BENCHMARKS_DIR / "benchmark_results.json"
OUTPUT_IMG = BENCHMARKS_DIR / "benchmark_comparison.png"

if JSON_FILE.exists():
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
else:
    data = {
        "indexing_duration_ms": {"Python": 42.05, "Java": 164.12, "C": 40.26},
        "query_latency_ms": {
            "Monolithic (JSON RAM)": 319.154,
            "Hierarchical (Files/IO)": 47.916,
            "SQLite (B-Tree Index)": 1.902
        },
        "datalake_lookup_ms": {
            "partition_time_ms": 0.3777,
            "partition_id_ms": 0.0277
        }
    }

plt.rcParams.update({
    'font.sans-serif': 'Segoe UI',
    'font.family': 'sans-serif',
    'axes.edgecolor': '#cccccc',
    'axes.linewidth': 0.8
})

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('Stage 1 — Comprehensive Performance and Architecture Comparison', fontsize=16, fontweight='bold', y=0.98)



ax1 = axes[0, 0]
idx_data = data.get("indexing_duration_ms", {"Python": 42.05, "Java": 164.12, "C": 40.26})
langs = list(idx_data.keys())
idx_times = [idx_data[l] for l in langs]
colors_idx = ['#2ca02c', '#ff7f0e', '#1f77b4']

bars1 = ax1.bar(langs, idx_times, color=colors_idx, width=0.5, edgecolor='black', linewidth=0.6)
ax1.set_title('1. Indexing Duration (ms)', fontsize=12, fontweight='bold', pad=10)
ax1.set_ylabel('Total Time (milliseconds)')
ax1.grid(axis='y', linestyle='--', alpha=0.4)

for bar in bars1:
    h = bar.get_height()
    ax1.annotate(f"{h:.2f} ms",
                 xy=(bar.get_x() + bar.get_width() / 2, h),
                 xytext=(0, 4), textcoords="offset points",
                 ha='center', va='bottom', fontsize=10, fontweight='bold')



ax2 = axes[0, 1]
q_data = {
    "SQLite (B-Tree)": 1.902,
    "Hierarchical (I/O)": 47.916,
    "Monolithic (JSON)": 319.154
}
q_keys = list(q_data.keys())
q_times = list(q_data.values())
colors_q = ['#2ca02c', '#1f77b4', '#d62728']

bars2 = ax2.bar(q_keys, q_times, color=colors_q, width=0.5, edgecolor='black', linewidth=0.6)
ax2.set_yscale('log')
ax2.set_title('2. Query Latency per Model (ms, log scale)', fontsize=12, fontweight='bold', pad=10)
ax2.set_ylabel('Response Time (ms)')
ax2.grid(axis='y', which='both', linestyle='--', alpha=0.3)

for bar, val in zip(bars2, q_times):
    ax2.annotate(f"{val:.2f} ms",
                 xy=(bar.get_x() + bar.get_width() / 2, val),
                 xytext=(0, 4), textcoords="offset points",
                 ha='center', va='bottom', fontsize=10, fontweight='bold')



ax3 = axes[1, 0]
dl_data = data.get("datalake_lookup_ms", {"partition_time_ms": 0.3777, "partition_id_ms": 0.0277})
dl_names = ['Time Partition\nO(N) Walk', 'ID Partition\nO(1) Direct']
dl_times = [dl_data.get("partition_time_ms", 0.3777), dl_data.get("partition_id_ms", 0.0277)]
colors_dl = ['#d62728', '#2ca02c']

bars3 = ax3.bar(dl_names, dl_times, color=colors_dl, width=0.45, edgecolor='black', linewidth=0.6)
ax3.set_title('3. Data Lake Lookup Cost (ms)', fontsize=12, fontweight='bold', pad=10)
ax3.set_ylabel('Lookup Cost (ms)')
ax3.grid(axis='y', linestyle='--', alpha=0.4)

for bar in bars3:
    h = bar.get_height()
    ax3.annotate(f"{h:.4f} ms",
                 xy=(bar.get_x() + bar.get_width() / 2, h),
                 xytext=(0, 4), textcoords="offset points",
                 ha='center', va='bottom', fontsize=10, fontweight='bold')


ax4 = axes[1, 1]
mem_data = {"Python": 29.07, "C": 94.40, "Java": 979.81}
mem_langs = list(mem_data.keys())
mem_values = list(mem_data.values())
colors_mem = ['#2ca02c', '#1f77b4', '#d62728']

bars4 = ax4.bar(mem_langs, mem_values, color=colors_mem, width=0.5, edgecolor='black', linewidth=0.6)
ax4.set_title('4. Maximum RAM Memory Usage (MB)', fontsize=12, fontweight='bold', pad=10)
ax4.set_ylabel('Allocated RAM (MB)')
ax4.grid(axis='y', linestyle='--', alpha=0.4)

for bar in bars4:
    h = bar.get_height()
    ax4.annotate(f"{h:.1f} MB",
                 xy=(bar.get_x() + bar.get_width() / 2, h),
                 xytext=(0, 4), textcoords="offset points",
                 ha='center', va='bottom', fontsize=10, fontweight='bold')

plt.tight_layout(rect=[0, 0.03, 1, 0.95])
plt.savefig(OUTPUT_IMG, dpi=300)
plt.close()
print(f"[SUCCESS] Plot successfully generated at: {OUTPUT_IMG}")
