import time
import csv
import subprocess
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

    def run_command(self, language: str, component: str, variant: str, num_books: int, command: list):
        """Ejecuta un comando del sistema midiendo tiempo y memoria consumida."""
        print(f"\n[BENCHMARK START] Ejecutando {language} ({variant})...")
        
        start_time = time.perf_counter()
        
        # Iniciar el proceso hijo
        process = subprocess.Popen(command, cwd=BASE_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        max_mem_mb = 0.0
        try:
            ps_proc = psutil.Process(process.pid)
            while process.poll() is None:
                try:
                    mem_info = ps_proc.memory_info().rss / (1024 * 1024)
                    if mem_info > max_mem_mb:
                        max_mem_mb = mem_info
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                time.sleep(0.05)
        except Exception as e:
            print(f"[WARNING] No se pudo monitorear memoria continua: {e}")

        process.communicate()
        end_time = time.perf_counter()

        execution_time = round(end_time - start_time, 4)
        max_mem_mb = round(max_mem_mb, 2)

        with open(self.output_csv, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                time.strftime("%Y-%m-%d %H:%M:%S"),
                language, component, variant, num_books,
                execution_time, max_mem_mb
            ])

        print(f"[BENCHMARK COMPLETED] {language} ({variant}) | Libros: {num_books} | Tiempo: {execution_time}s | RAM Máx: {max_mem_mb}MB")

if __name__ == "__main__":
    runner = BenchmarkRunner()
    num_books = 25

    # 1. Benchmark C
    c_exe = BASE_DIR / "main_c.exe"
    if not c_exe.exists():
        print("[BUILD] Compilando C...")
        subprocess.run(["gcc", "src/C/main.c", "-o", "main_c.exe"], cwd=BASE_DIR, check=True)
    runner.run_command("C", "Indexer", "Triple Storage (JSON/Folders/TSV)", num_books, [str(c_exe)])

    # 2. Benchmark Java
    bin_dir = BASE_DIR / "bin"
    if not (bin_dir / "Main.class").exists():
        print("[BUILD] Compilando Java...")
        subprocess.run(["javac", "-d", "bin", "src/java/Main.java", "src/java/indexer/InvertedIndexer.java"], cwd=BASE_DIR, check=True)
    runner.run_command("Java", "Indexer", "Triple Storage (JSON/Folders/TSV)", num_books, ["java", "-cp", "bin", "Main"])

    # 3. Benchmark Python (si existe un script de indexación en src/python/)
    py_indexer = BASE_DIR / "src" / "python" / "main.py"
    if py_indexer.exists():
        runner.run_command("Python", "Indexer", "Triple Storage", num_books, ["python", str(py_indexer)])

    print("\n[SUCCESS] Benchmarking finalizado con éxito. Datos guardados en benchmarks/metrics.csv")