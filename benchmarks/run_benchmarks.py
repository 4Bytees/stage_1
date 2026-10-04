import os
import sys
import time
import json
import sqlite3
import subprocess
from pathlib import Path

# Configuring paths relative to the project root
BASE_DIR = Path(__file__).resolve().parent.parent
DATAMARTS_DIR = BASE_DIR / "datamarts"
DATALAKE_DIR = BASE_DIR / "datalake"
SAMPLE_DATA_DIR = BASE_DIR / "sample_data"
BENCHMARKS_DIR = BASE_DIR / "benchmarks"
BIN_DIR = BASE_DIR / "bin"

# Test criteria for measuring query latency
TEST_TERMS = ["gutenberg", "project", "electronic", "foundation", "states", "united", "life", "time"]

def get_dir_size_bytes(path: Path) -> int:
    """Calculates the total size in bytes of a file or folder recursively."""
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())

# -------------------------------------------------------------
# 1. BENCHMARK: INDEXING SPEED AND THROUGHPUT
# -------------------------------------------------------------
def benchmark_indexing_speed():
    print("\n" + "="*70)
    print(" 1. BENCHMARK: INDEXING TIME BY LANGUAGE")
    print("="*70)

    results = {}
    py_exec = sys.executable

    # A) Python
    print(" -> [1/3] Running Python indexer (processing books)...", end="", flush=True)
    py_script = BASE_DIR / "src" / "python" / "indexer" / "indexer.py"
    if py_script.exists():
        start = time.perf_counter()
        subprocess.run([py_exec, str(py_script)], capture_output=True, text=True, cwd=str(BASE_DIR))
        py_duration = (time.perf_counter() - start) * 1000
        results["Python"] = round(py_duration, 2)
        print(f" Done ({results['Python']:.0f} ms)")
    else:
        results["Python"] = None
        print(" Skipped (not found)")

    # B) Java
    print(" -> [2/3] Running Java indexer...", end="", flush=True)
    java_bin = BIN_DIR / "Main.class"
    if java_bin.exists():
        start = time.perf_counter()
        subprocess.run(["java", "-cp", "bin", "Main"], capture_output=True, text=True, cwd=str(BASE_DIR))
        java_duration = (time.perf_counter() - start) * 1000
        results["Java"] = round(java_duration, 2)
        print(f" Done ({results['Java']:.0f} ms)")
    else:
        results["Java"] = None
        print(" Skipped (bin/Main.class not compiled)")

    # C) C
    print(" -> [3/3] Running C indexer...", end="", flush=True)
    c_bin = BIN_DIR / "indexer_c.exe"
    if c_bin.exists():
        start = time.perf_counter()
        subprocess.run([str(c_bin)], capture_output=True, text=True, cwd=str(BASE_DIR))
        c_duration = (time.perf_counter() - start) * 1000
        results["C"] = round(c_duration, 2)
        print(f" Done ({results['C']:.0f} ms)")
    else:
        results["C"] = None
        print(" Skipped (bin/indexer_c.exe not compiled)")

    print("\n" + f"{'Language':<15} | {'Total Time (ms)':>18} | {'Relative Speedup':>18}")
    print("-" * 57)
    base_time = results.get("Python") or 1.0
    for lang, duration in results.items():
        if duration is not None:
            speedup = f"{base_time / max(duration, 0.01):.2f}x"
            print(f"{lang:<15} | {duration:>18.2f} | {speedup:>18}")
        else:
            print(f"{lang:<15} | {'Not compiled':>18} | {'N/A':>18}")

    return results

# -------------------------------------------------------------
# 2. BENCHMARK: STORAGE FOOTPRINT
# -------------------------------------------------------------
def benchmark_storage_footprint():
    print("\n" + "="*70)
    print(" 2. BENCHMARK: STORAGE FOOTPRINT")
    print("="*70)

    structures = {
        "Python Monolithic (JSON)": DATAMARTS_DIR / "inverted_index.json",
        "Python Hierarchical (Folders)": DATAMARTS_DIR / "inverted_index_folders",
        "Python Relational (SQLite)": DATAMARTS_DIR / "inverted_index.db",
        "Java Monolithic (JSON)": DATAMARTS_DIR / "inverted_index_java.json",
        "Java Hierarchical (Folders)": DATAMARTS_DIR / "inverted_index_folders_java",
        "Java Tabular (TSV)": DATAMARTS_DIR / "inverted_index_java.tsv",
        "C Monolithic (JSON)": DATAMARTS_DIR / "inverted_index_c.json",
        "C Hierarchical (Folders)": DATAMARTS_DIR / "inverted_index_folders_c",
        "C Tabular (TSV)": DATAMARTS_DIR / "inverted_index_c.tsv",
    }

    results = {}
    print(f"{'Structure / Datamart':<35} | {'Size (KB)':>14} | {'Size (MB)':>14}")
    print("-" * 69)
    for name, path in structures.items():
        size_bytes = get_dir_size_bytes(path)
        size_kb = size_bytes / 1024
        size_mb = size_kb / 1024
        results[name] = {"bytes": size_bytes, "kb": round(size_kb, 2), "mb": round(size_mb, 3)}
        print(f"{name:<35} | {size_kb:>14.2f} | {size_mb:>14.3f}")

    return results

# -------------------------------------------------------------
# 3. BENCHMARK: QUERY LATENCY
# -------------------------------------------------------------
def benchmark_query_latency():
    print("\n" + "="*70)
    print(" 3. BENCHMARK: QUERY LATENCY")
    print("="*70)

    results = {}
    n_terms = len(TEST_TERMS)

    # A) Monolithic (JSON)
    json_path = DATAMARTS_DIR / "inverted_index.json"
    if json_path.exists():
        start = time.perf_counter()
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for term in TEST_TERMS:
                _ = data.get(term, None)
        json_time = (time.perf_counter() - start) * 1000
        results["Monolithic (JSON RAM)"] = round(json_time, 3)
    else:
        results["Monolithic (JSON RAM)"] = None

    # B) Hierarchical (Folders)
    folder_path = DATAMARTS_DIR / "inverted_index_folders"
    if folder_path.exists():
        start = time.perf_counter()
        for term in TEST_TERMS:
            letter = term[0].upper()
            term_file = folder_path / letter / f"{term}.txt"
            if term_file.exists():
                _ = term_file.read_text(encoding="utf-8")
        folder_time = (time.perf_counter() - start) * 1000
        results["Hierarchical (Files/IO)"] = round(folder_time, 3)
    else:
        results["Hierarchical (Files/IO)"] = None

    # C) Relational (SQLite B-Tree)
    db_path = DATAMARTS_DIR / "inverted_index.db"
    if db_path.exists():
        start = time.perf_counter()
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        for term in TEST_TERMS:
            cur.execute("SELECT book_id, frequency, positions FROM inverted_index WHERE term = ?", (term,))
            _ = cur.fetchall()
        conn.close()
        db_time = (time.perf_counter() - start) * 1000
        results["SQLite (B-Tree Index)"] = round(db_time, 3)
    else:
        results["SQLite (B-Tree Index)"] = None

    # D) Tabular (sequential TSV)
    tsv_path = DATAMARTS_DIR / "inverted_index_c.tsv"
    if not tsv_path.exists():
        tsv_path = DATAMARTS_DIR / "inverted_index_java.tsv"
    if tsv_path.exists():
        start = time.perf_counter()
        with open(tsv_path, "r", encoding="utf-8", errors="ignore") as f:
            terms_set = set(TEST_TERMS)
            _ = [line for line in f if line.split("\t")[0] in terms_set]
        tsv_time = (time.perf_counter() - start) * 1000
        results["Tabular TSV (Sequential Scan)"] = round(tsv_time, 3)
    else:
        results["Tabular TSV (Sequential Scan)"] = None

    print(f"{'Evaluated Structure':<35} | {'Total Time (ms)':>18} | {'Avg/Term (ms)':>18}")
    print("-" * 77)
    for est, total_ms in results.items():
        if total_ms is not None:
            avg_ms = total_ms / n_terms
            print(f"{est:<35} | {total_ms:>18.3f} | {avg_ms:>18.3f}")
        else:
            print(f"{est:<35} | {'Not generated':>18} | {'N/A':>18}")

    return results

# -------------------------------------------------------------
# 4. BENCHMARK: DATALAKE ACCESS PERFORMANCE (LOOKUP COST)
# -------------------------------------------------------------
def benchmark_datalake_lookup():
    print("\n" + "="*70)
    print(" 4. BENCHMARK: DATALAKE LOOKUP COST")
    print("="*70)

    time_dir = DATALAKE_DIR / "time"
    id_dir = DATALAKE_DIR / "id"

    # Select a test book
    sample_files = list(SAMPLE_DATA_DIR.glob("*_body.txt")) if SAMPLE_DATA_DIR.exists() else []
    sample_id = int(sample_files[0].stem.split("_")[0]) if sample_files else 6

    # A) Time partitioning: requires a recursive os.walk scan
    time_cost_ms = 0.0
    if time_dir.exists():
        start = time.perf_counter()
        found = None
        for root, _, files in os.walk(time_dir):
            if f"{sample_id}_body.txt" in files:
                found = Path(root) / f"{sample_id}_body.txt"
                break
        time_cost_ms = (time.perf_counter() - start) * 1000

    # B) ID partitioning: direct mathematical path calculation O(1)
    id_cost_ms = 0.0
    id_str = f"{sample_id:04d}"
    parts = [id_str[i:i+2] for i in range(0, len(id_str), 2)]
    calculated_path = id_dir
    for p in parts:
        calculated_path = calculated_path / p

    start = time.perf_counter()
    target_file = calculated_path / f"{sample_id}_body.txt"
    _ = target_file.exists()
    id_cost_ms = (time.perf_counter() - start) * 1000

    print(f"{'Partitioning Strategy':<35} | {'Lookup Cost (ms)':>20} | {'Complexity':>15}")
    print("-" * 76)
    print(f"{'Time Partition (time/YYYY/HH)':<35} | {time_cost_ms:>20.4f} | {'O(N) Walk':>15}")
    print(f"{'ID Partition (id/XX/YY)':<35} | {id_cost_ms:>20.4f} | {'O(1) Direct':>15}")

    return {
        "partition_time_ms": round(time_cost_ms, 4),
        "partition_id_ms": round(id_cost_ms, 4)
    }

# -------------------------------------------------------------
# MAIN EXECUTION AND EXPORT
# -------------------------------------------------------------
if __name__ == "__main__":
    BENCHMARKS_DIR.mkdir(parents=True, exist_ok=True)

    idx_results = benchmark_indexing_speed()
    storage_results = benchmark_storage_footprint()
    query_results = benchmark_query_latency()
    datalake_results = benchmark_datalake_lookup()

    all_metrics = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "indexing_duration_ms": idx_results,
        "storage_footprint": storage_results,
        "query_latency_ms": query_results,
        "datalake_lookup_ms": datalake_results
    }

    output_json = BENCHMARKS_DIR / "benchmark_results.json"
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(all_metrics, f, indent=2)

    print("\n" + "="*70)
    print(f"[SUCCESS] All tests have finished.")
    print(f"Results saved for the report in: {output_json}")
    print("="*70)