import time
import csv
import sys
import psutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
BENCHMARKS_DIR = BASE_DIR / "benchmarks"
RESULTS_CSV = BENCHMARKS_DIR / "metrics.csv"

BENCHMARKS_DIR.mkdir(parents=True, exist_ok=True)

class BenchmarkRunner:
    def __init__(self, output_csv=RESULTS_CSV):
        self.output_csv = output_csv
        self._init_csv()

    def _init_csv(self):
        """Crea la cabecera del CSV si el archivo no existe."""
        if not self.output_csv.exists():
            with open(self.output_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "language", "component", 
                    "strategy_variant", "num_books", 
                    "execution_time_sec", "memory_mb"
                ])

    def measure(self, language: str, component: str, variant: str, num_books: int, func, *args, **kwargs):
        """Mide tiempo de ejecución y consumo de memoria RAM."""
        process = psutil.Process()
        mem_before = process.memory_info().rss / (1024 * 1024)
        
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()

        mem_after = process.memory_info().rss / (1024 * 1024)
        execution_time = round(end_time - start_time, 4)
        mem_used = round(max(0, mem_after - mem_before), 2)

        with open(self.output_csv, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                time.strftime("%Y-%m-%d %H:%M:%S"),
                language, component, variant, num_books,
                execution_time, mem_used
            ])

        print(f"[BENCHMARK] {component} ({variant}) | Libros: {num_books} | Tiempo: {execution_time}s | RAM: {mem_used}MB")
        return result

if __name__ == "__main__":
    runner = BenchmarkRunner()
    print("Módulo de Benchmarks preparado en benchmarks/metrics.csv")