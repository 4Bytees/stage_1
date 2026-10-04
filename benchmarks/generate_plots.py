import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
CSV_FILE = BASE_DIR / "benchmarks" / "metrics.csv"
OUTPUT_IMG = BASE_DIR / "benchmarks" / "benchmark_comparison.png"

# Cargar últimas 3 mediciones
df = pd.read_csv(CSV_FILE)
latest_df = df.tail(3)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

# Gráfico de tiempo ejecución
ax1.bar(latest_df['language'], latest_df['execution_time_sec'], color=['#1f77b4', '#ff7f0e', '#2ca02c'])
ax1.set_title('Tiempo de Ejecución (Segundos)')
ax1.set_ylabel('Segundos')
for bar in ax1.patches:
    ax1.annotate(f"{bar.get_height():.2f}s", (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                 ha='center', va='bottom')

# Gráfico de consumo de memoria RAM
ax2.bar(latest_df['language'], latest_df['memory_mb'], color=['#1f77b4', '#ff7f0e', '#2ca02c'])
ax2.set_title('Consumo Máximo de RAM (MB)')
ax2.set_ylabel('MB')
for bar in ax2.patches:
    ax2.annotate(f"{bar.get_height():.1f}MB", (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                 ha='center', va='bottom')

plt.tight_layout()
plt.savefig(OUTPUT_IMG)
print(f"[EXITO] Gráfica guardada en: {OUTPUT_IMG}")