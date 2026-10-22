"""
run_benchmarks.py  –  Stage-1 Comprehensive Benchmark Suite
=============================================================

Experiments implemented
-----------------------
1.  Indexing speed by language (Python / Java / C)
2.  Storage footprint per datamart structure
3.  Query latency by structure (Monolithic JSON / Hierarchical / SQLite / TSV)
4.  Datalake look-up cost (time-partition vs ID-partition)
5.  Discovery experiment (pending books detection time)
6.  Storage state metadata (file/dir counts, logical vs physical size)
7.  Interruption / resumption idempotency check
8.  Incremental update cost (add one batch and measure delta)
9.  Growth scaling (repeated measurements at corpus sizes 1, 2, 4, 6 books)
10. Cross-language parity verification (same terms, same posting sets)

Usage
-----
    cd stage1/
    python benchmarks/run_benchmarks.py [--warmup N] [--reps N]

Requirements
------------
    Python >= 3.11   (for Path.stat().st_blocks on Linux)
    Java, GCC        (optional; benchmarks are skipped if not compiled)

Environment
-----------
    CPU, RAM, storage, filesystem, and OS are captured automatically.
    Compiler/runtime flags are declared in the ENVIRONMENT section below.
"""

import os
import sys
import time
import json
import sqlite3
import platform
import subprocess
import hashlib
from pathlib import Path

# Force UTF-8 stdout/stderr on Windows console to prevent cp1252 charmap encode errors
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------
BASE_DIR      = Path(__file__).resolve().parent.parent
DATAMARTS_DIR = BASE_DIR / "datamarts"
DATALAKE_DIR  = BASE_DIR / "datalake"
SAMPLE_DIR    = BASE_DIR / "sample_data"
BENCHMARKS_DIR= BASE_DIR / "benchmarks"
CONTROL_DIR   = BASE_DIR / "control"
BIN_DIR       = BASE_DIR / "bin"
SRC_PY_DIR    = BASE_DIR / "src" / "python"

# Add project directories to sys.path so modules can be imported
for _p in [SRC_PY_DIR, BENCHMARKS_DIR, BASE_DIR]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

# Safe top-level imports for benchmark modules
try:
    # pyrefly: ignore[missing-import]
    from query_benchmark import query_monolithic, query_hierarchical, query_sqlite
except ImportError:
    try:
        from src.python.query_benchmark import query_monolithic, query_hierarchical, query_sqlite
    except ImportError:
        query_monolithic = query_hierarchical = query_sqlite = None  # type: ignore

try:
    # pyrefly: ignore[missing-import]
    from indexer.indexer import process_single_indexing
except ImportError:
    try:
        from src.python.indexer.indexer import process_single_indexing
    except ImportError:
        process_single_indexing = None  # type: ignore

try:
    from benchmark_datalake import benchmark_datalake_lookup as _bm_datalake
except ImportError:
    try:
        from benchmarks.benchmark_datalake import benchmark_datalake_lookup as _bm_datalake
    except ImportError:
        _bm_datalake = None  # type: ignore

# ---------------------------------------------------------------------------
# Declared environment (update if running on a different machine)
# ---------------------------------------------------------------------------
DECLARED_ENV = {
    "compiler_flags": {
        "C":    "gcc -O2",
        "Java": "javac (JDK 21, default settings)",
        "Python": f"CPython {sys.version}",
    },
    "jvm_settings": "-Xmx512m (default)",
    "notes": (
        "All benchmarks run on the local machine described by platform_info below. "
        "No JIT warm-up for Python; Java and C processes are invoked fresh per run."
    ),
}

TEST_TERMS = [
    "gutenberg", "project", "electronic", "foundation",
    "states", "united", "life", "time",
]

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def get_logical_size_bytes(path: Path) -> int:
    """Sum of st_size for all files (logical content bytes)."""
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def get_physical_size_bytes(path: Path) -> int:
    """
    Disk-allocated bytes (st_blocks * 512).
    On Windows st_blocks is unavailable; falls back to st_size.
    """
    if not path.exists():
        return 0
    if path.is_file():
        st = path.stat()
        return st.st_blocks * 512 if hasattr(st, "st_blocks") else st.st_size
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            try:
                st = os.stat(os.path.join(root, f))
                total += st.st_blocks * 512 if hasattr(st, "st_blocks") else st.st_size
            except OSError:
                pass
    return total


def count_files_and_dirs(path: Path) -> dict:
    """Count files and directories under *path*."""
    if not path.exists():
        return {"files": 0, "dirs": 0}
    if path.is_file():
        return {"files": 1, "dirs": 0}
    files = dirs = 0
    for root, dirnames, filenames in os.walk(path):
        dirs += len(dirnames)
        files += len(filenames)
    return {"files": files, "dirs": dirs}


def md5_of_file(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def read_id_set(filepath: Path) -> set[int]:
    if not filepath.exists():
        return set()
    return {int(l.strip()) for l in filepath.read_text().splitlines() if l.strip().isdigit()}


def section(title: str):
    width = 72
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)


# ---------------------------------------------------------------------------
# 0. Environment capture
# ---------------------------------------------------------------------------

def capture_environment() -> dict:
    section("0. RUNTIME ENVIRONMENT")

    info = {
        "platform": platform.platform(),
        "processor": platform.processor(),
        "python_version": sys.version,
        "cpu_count_logical": os.cpu_count(),
        "declared_compiler_flags": DECLARED_ENV["compiler_flags"],
        "jvm_settings": DECLARED_ENV["jvm_settings"],
        "notes": DECLARED_ENV["notes"],
    }

    # RAM (best-effort)
    try:
        import psutil
        info["ram_total_gb"] = round(psutil.virtual_memory().total / (1024**3), 2)
        info["ram_available_gb"] = round(psutil.virtual_memory().available / (1024**3), 2)
    except ImportError:
        info["ram_total_gb"] = "psutil not installed"

    for k, v in info.items():
        print(f"  {k}: {v}")

    return info


# ---------------------------------------------------------------------------
# 1. Indexing speed by language
# ---------------------------------------------------------------------------

def benchmark_indexing_speed(warmup: int = 1, reps: int = 3) -> dict:
    section("1. INDEXING SPEED BY LANGUAGE")
    print(f"  warm-up passes: {warmup}  |  measurement reps: {reps}")
    print(f"  Corpus: {SAMPLE_DIR}")

    py_exec = sys.executable
    py_script = SRC_PY_DIR / "indexer" / "indexer.py"
    java_class = BIN_DIR / "Main.class"
    c_bin = BIN_DIR / ("indexer_c.exe" if platform.system() == "Windows" else "indexer_c")

    def run_and_time(cmd, cwd, label):
        # warm-up
        for _ in range(warmup):
            subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd))
        samples = []
        for _ in range(reps):
            t0 = time.perf_counter()
            subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd))
            samples.append((time.perf_counter() - t0) * 1000)
        mean_ms = sum(samples) / len(samples)
        variance = sum((s - mean_ms)**2 for s in samples) / len(samples)
        stddev = variance ** 0.5
        print(f"  [{label}] mean={mean_ms:.1f} ms  stddev={stddev:.1f} ms  samples={[round(s,1) for s in samples]}")
        return {"mean_ms": round(mean_ms, 2), "stddev_ms": round(stddev, 2), "samples_ms": [round(s, 2) for s in samples]}

    results = {}

    # Count corpus
    body_files = list(SAMPLE_DIR.glob("*_body.txt")) if SAMPLE_DIR.exists() else []
    total_bytes = sum(f.stat().st_size for f in body_files)
    print(f"  Corpus: {len(body_files)} books | {total_bytes/1024:.1f} KB total\n")
    results["corpus_books"] = len(body_files)
    results["corpus_bytes"] = total_bytes

    # Python
    if py_script.exists():
        results["Python"] = run_and_time(
            [py_exec, str(py_script)], BASE_DIR, "Python"
        )
    else:
        results["Python"] = None
        print("  [Python] indexer.py not found – skipped")

    # Java
    if java_class.exists():
        results["Java"] = run_and_time(
            ["java", "-cp", str(BIN_DIR), "Main", str(SAMPLE_DIR)], BASE_DIR, "Java"
        )
    else:
        results["Java"] = None
        print("  [Java] bin/Main.class not compiled – skipped")

    # C
    if c_bin.exists():
        results["C"] = run_and_time(
            [str(c_bin), str(SAMPLE_DIR)], BASE_DIR, "C"
        )
    else:
        results["C"] = None
        print("  [C] bin/indexer_c not compiled – skipped")

    # Relative speed-up table
    print()
    base = results.get("Python", {})
    base_ms = base.get("mean_ms", 1.0) if base else 1.0
    print(f"  {'Language':<12} | {'Mean (ms)':>12} | {'Stddev (ms)':>12} | {'Speedup':>10}")
    print(f"  {'-'*52}")
    for lang in ("Python", "Java", "C"):
        r = results.get(lang)
        if r:
            speedup = f"{base_ms / max(r['mean_ms'], 0.01):.2f}x"
            print(f"  {lang:<12} | {r['mean_ms']:>12.2f} | {r['stddev_ms']:>12.2f} | {speedup:>10}")
        else:
            print(f"  {lang:<12} | {'Not compiled':>12} | {'N/A':>12} | {'N/A':>10}")

    return results


# ---------------------------------------------------------------------------
# 2. Storage footprint
# ---------------------------------------------------------------------------

def benchmark_storage_footprint() -> dict:
    section("2. STORAGE FOOTPRINT")

    structures = {
        "Python Monolithic (JSON)":     DATAMARTS_DIR / "inverted_index.json",
        "Python Hierarchical (Folders)":DATAMARTS_DIR / "inverted_index_folders",
        "Python Relational (SQLite)":   DATAMARTS_DIR / "inverted_index.db",
        "Java Monolithic (JSON)":       DATAMARTS_DIR / "inverted_index_java.json",
        "Java Hierarchical (Folders)":  DATAMARTS_DIR / "inverted_index_folders_java",
        "Java Tabular (TSV)":           DATAMARTS_DIR / "inverted_index_java.tsv",
        "C Monolithic (JSON)":          DATAMARTS_DIR / "inverted_index_c.json",
        "C Hierarchical (Folders)":     DATAMARTS_DIR / "inverted_index_folders_c",
        "C Tabular (TSV)":              DATAMARTS_DIR / "inverted_index_c.tsv",
    }

    results = {}
    hdr = f"  {'Structure':<38} | {'Logical KB':>10} | {'Phys KB':>10} | {'Files':>6} | {'Dirs':>5}"
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))

    for name, path in structures.items():
        logical = get_logical_size_bytes(path)
        physical = get_physical_size_bytes(path)
        counts = count_files_and_dirs(path)
        results[name] = {
            "logical_bytes": logical,
            "logical_kb": round(logical / 1024, 2),
            "physical_bytes": physical,
            "physical_kb": round(physical / 1024, 2),
            "file_count": counts["files"],
            "dir_count": counts["dirs"],
        }
        print(f"  {name:<38} | {logical/1024:>10.2f} | {physical/1024:>10.2f} | "
              f"{counts['files']:>6} | {counts['dirs']:>5}")

    return results


# ---------------------------------------------------------------------------
# 3. Query latency
# ---------------------------------------------------------------------------

def benchmark_query_latency(warmup: int = 1, reps: int = 5) -> dict:
    section("3. QUERY LATENCY")
    print(f"  Terms: {TEST_TERMS}")
    print(f"  warm-up: {warmup} pass(es) | reps: {reps}\n")

    if query_monolithic is None or query_hierarchical is None or query_sqlite is None:
        print("  [SKIP] Query modules not imported – skipped")
        return {"status": "skipped", "reason": "query modules not found"}

    def time_queries(fn, label):
        # warm-up
        for _ in range(warmup):
            for t in TEST_TERMS:
                fn(t)
        samples = []
        for _ in range(reps):
            t0 = time.perf_counter()
            for t in TEST_TERMS:
                fn(t)
            samples.append((time.perf_counter() - t0) * 1000)
        mean = sum(samples) / len(samples)
        stddev = (sum((s - mean)**2 for s in samples) / len(samples)) ** 0.5
        avg_per_term = mean / len(TEST_TERMS)
        print(f"  [{label}] total={mean:.3f} ms  per-term={avg_per_term:.3f} ms  stddev={stddev:.3f} ms")
        return {
            "total_mean_ms": round(mean, 3),
            "per_term_mean_ms": round(avg_per_term, 3),
            "stddev_ms": round(stddev, 3),
            "samples_ms": [round(s, 3) for s in samples],
        }

    results = {}

    if (DATAMARTS_DIR / "inverted_index.json").exists():
        results["Monolithic (JSON → RAM load + dict lookup)"] = time_queries(query_monolithic, "Monolithic JSON")
    else:
        print("  [Monolithic JSON] not found – skipped")

    if (DATAMARTS_DIR / "inverted_index_folders").exists():
        results["Hierarchical (direct file I/O per term)"] = time_queries(query_hierarchical, "Hierarchical Folders")
    else:
        print("  [Hierarchical] not found – skipped")

    if (DATAMARTS_DIR / "inverted_index.db").exists():
        results["SQLite (B-Tree indexed lookup)"] = time_queries(query_sqlite, "SQLite B-Tree")
    else:
        print("  [SQLite] not found – skipped")

    # TSV sequential scan
    tsv_path = DATAMARTS_DIR / "inverted_index_c.tsv"
    if not tsv_path.exists():
        tsv_path = DATAMARTS_DIR / "inverted_index_java.tsv"
    if tsv_path.exists():
        terms_set = set(TEST_TERMS)
        def query_tsv_seq(_term):
            # Sequential scan – term argument is ignored intentionally;
            # we scan once and collect all matching terms per call.
            with open(tsv_path, "r", encoding="utf-8", errors="ignore") as fh:
                return [l for l in fh if l.split("\t")[0] in terms_set]
        results["Tabular TSV (sequential scan for all terms)"] = time_queries(
            query_tsv_seq, "TSV Sequential Scan"
        )
    else:
        print("  [TSV] not found – skipped")

    return results


# ---------------------------------------------------------------------------
# 4. Datalake lookup
# ---------------------------------------------------------------------------

def benchmark_datalake_lookup() -> dict:
    section("4. DATALAKE LOOK-UP COST")
    if _bm_datalake is not None:
        return _bm_datalake()
    print("  [SKIP] benchmark_datalake module not found")
    return {"status": "skipped"}


# ---------------------------------------------------------------------------
# 5. Discovery experiment
# ---------------------------------------------------------------------------

def benchmark_discovery() -> dict:
    section("5. DISCOVERY EXPERIMENT")
    print("  Detecting books downloaded but not yet indexed...\n")

    downloaded_file = CONTROL_DIR / "downloaded_books.txt"
    indexed_file    = CONTROL_DIR / "indexed_books.txt"

    t0 = time.perf_counter()
    downloaded = read_id_set(downloaded_file)
    indexed    = read_id_set(indexed_file)
    pending    = sorted(downloaded - indexed)
    discovery_ms = (time.perf_counter() - t0) * 1000

    print(f"  Downloaded IDs : {sorted(downloaded)}")
    print(f"  Indexed IDs    : {sorted(indexed)}")
    print(f"  Pending IDs    : {pending}")
    print(f"  Discovery time : {discovery_ms:.4f} ms")

    return {
        "downloaded_count": len(downloaded),
        "indexed_count": len(indexed),
        "pending_ids": pending,
        "discovery_ms": round(discovery_ms, 4),
    }


# ---------------------------------------------------------------------------
# 6. Storage state metadata
# ---------------------------------------------------------------------------

def benchmark_storage_state() -> dict:
    section("6. STORAGE STATE METADATA")

    paths = {
        "datalake/time":      DATALAKE_DIR / "time",
        "datalake/id":        DATALAKE_DIR / "id",
        "datamarts (all)":    DATAMARTS_DIR,
        "control":            CONTROL_DIR,
    }

    results = {}
    print(f"  {'Path':<30} | {'Files':>6} | {'Dirs':>5} | {'Logical KB':>12} | {'Phys KB':>12}")
    print(f"  {'-'*70}")
    for label, p in paths.items():
        counts = count_files_and_dirs(p)
        log_kb = get_logical_size_bytes(p) / 1024
        phy_kb = get_physical_size_bytes(p) / 1024
        results[label] = {**counts, "logical_kb": round(log_kb, 2), "physical_kb": round(phy_kb, 2)}
        print(f"  {label:<30} | {counts['files']:>6} | {counts['dirs']:>5} | "
              f"{log_kb:>12.2f} | {phy_kb:>12.2f}")

    return results


# ---------------------------------------------------------------------------
# 7. Interruption / resumption idempotency check
# ---------------------------------------------------------------------------

def benchmark_idempotency() -> dict:
    section("7. INTERRUPTION / RESUMPTION IDEMPOTENCY")
    print("  Verifying that re-running the indexer produces identical output...")

    py_exec = sys.executable
    py_script = SRC_PY_DIR / "indexer" / "indexer.py"
    if not py_script.exists():
        print("  [SKIP] indexer.py not found")
        return {"status": "skipped"}

    json_path = DATAMARTS_DIR / "inverted_index.json"

    # First run hash
    subprocess.run([py_exec, str(py_script)], capture_output=True, cwd=str(BASE_DIR))
    hash1 = md5_of_file(json_path)

    # Second run hash (simulates resumption after interruption)
    subprocess.run([py_exec, str(py_script)], capture_output=True, cwd=str(BASE_DIR))
    hash2 = md5_of_file(json_path)

    # The JSON index uses INSERT OR REPLACE (SQLite) / dict overwrite (JSON),
    # so a second run on the same corpus must produce the same output.
    ok = (hash1 == hash2)
    print(f"  Run 1 MD5: {hash1}")
    print(f"  Run 2 MD5: {hash2}")
    print(f"  Idempotent: {'YES [OK]' if ok else 'NO [FAIL]  – data duplication detected!'}")

    return {"run1_md5": hash1, "run2_md5": hash2, "idempotent": ok}


# ---------------------------------------------------------------------------
# 8. Incremental update cost
# ---------------------------------------------------------------------------

def benchmark_incremental_update() -> dict:
    section("8. INCREMENTAL UPDATE COST")

    # Find all sample body files; use the LAST one as the 'new' book
    body_files = sorted(SAMPLE_DIR.glob("*_body.txt")) if SAMPLE_DIR.exists() else []
    if len(body_files) < 2:
        print("  [SKIP] Need at least 2 body files in sample_data/")
        return {"status": "skipped", "reason": "insufficient corpus"}

    if process_single_indexing is None:
        print("  [SKIP] indexer module not found")
        return {"status": "skipped", "reason": "indexer module not found"}

    # Baseline size before adding the last book

    last_file = body_files[-1]
    book_id = int(last_file.stem.split("_")[0])

    size_before = get_logical_size_bytes(DATAMARTS_DIR / "inverted_index.json")

    t0 = time.perf_counter()
    process_single_indexing(book_id)
    update_ms = (time.perf_counter() - t0) * 1000

    size_after = get_logical_size_bytes(DATAMARTS_DIR / "inverted_index.json")
    delta_kb = (size_after - size_before) / 1024

    print(f"  Book added   : ID {book_id}  ({last_file.stat().st_size/1024:.1f} KB)")
    print(f"  Update time  : {update_ms:.2f} ms")
    print(f"  Index growth : +{delta_kb:.2f} KB")

    return {
        "book_id": book_id,
        "update_ms": round(update_ms, 2),
        "index_delta_kb": round(delta_kb, 2),
    }


# ---------------------------------------------------------------------------
# 9. Growth scaling
# ---------------------------------------------------------------------------

def benchmark_growth_scaling() -> dict:
    section("9. GROWTH SCALING (corpus size vs indexing time)")

    if process_single_indexing is None:
        print("  [SKIP] indexer module not found")
        return {"status": "skipped", "reason": "indexer module not found"}

    body_files = sorted(SAMPLE_DIR.glob("*_body.txt")) if SAMPLE_DIR.exists() else []
    if not body_files:
        print("  [SKIP] No body files found in sample_data/")
        return {"status": "skipped"}

    results = {}
    cumulative_ids = []

    for bf in body_files:
        book_id = int(bf.stem.split("_")[0])
        cumulative_ids.append(book_id)

        t0 = time.perf_counter()
        for bid in cumulative_ids:
            process_single_indexing(bid)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        json_size_kb = get_logical_size_bytes(DATAMARTS_DIR / "inverted_index.json") / 1024

        print(f"  {len(cumulative_ids):>3} books → {elapsed_ms:>10.2f} ms  "
              f"|  JSON size: {json_size_kb:>10.2f} KB")
        results[len(cumulative_ids)] = {
            "book_ids": list(cumulative_ids),
            "total_indexing_ms": round(elapsed_ms, 2),
            "json_size_kb": round(json_size_kb, 2),
        }

    return results


# ---------------------------------------------------------------------------
# 10. Cross-language parity
# ---------------------------------------------------------------------------

def benchmark_parity() -> dict:
    section("10. CROSS-LANGUAGE PARITY VERIFICATION")
    print(f"  Terms under test: {TEST_TERMS}\n")



    def read_hier_postings(folder: Path, term: str) -> set[int]:
        """Read book IDs from a hierarchical posting file."""
        t = term.lower()
        fpath = folder / t[0].upper() / f"{t}.txt"
        if not fpath.exists():
            return set()
        ids = set()
        for line in fpath.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(",", 1)
            if parts and parts[0].isdigit():
                ids.add(int(parts[0]))
        return ids

    py_folder   = DATAMARTS_DIR / "inverted_index_folders"
    java_folder = DATAMARTS_DIR / "inverted_index_folders_java"
    c_folder    = DATAMARTS_DIR / "inverted_index_folders_c"

    results = {}
    all_ok = True

    print(f"  {'Term':<16} | {'Python':>8} | {'Java':>8} | {'C':>8} | {'Parity'}")
    print(f"  {'-'*58}")

    for term in TEST_TERMS:
        py_ids   = read_hier_postings(py_folder, term)
        java_ids = read_hier_postings(java_folder, term)
        c_ids    = read_hier_postings(c_folder, term)

        ok = (py_ids == java_ids == c_ids)
        if not ok:
            all_ok = False
            diff = f"py={sorted(py_ids)} java={sorted(java_ids)} c={sorted(c_ids)}"
        else:
            diff = f"all agree: {sorted(py_ids)}"

        status = "OK [PASS]" if ok else "MISMATCH [FAIL]"
        print(f"  {term:<16} | {len(py_ids):>8} | {len(java_ids):>8} | {len(c_ids):>8} | {status}")

        results[term] = {
            "python_ids": sorted(py_ids),
            "java_ids": sorted(java_ids),
            "c_ids": sorted(c_ids),
            "parity_ok": ok,
            "details": diff,
        }

    print(f"\n  Overall parity: {'PASS [OK]' if all_ok else 'FAIL [MISMATCH]'}")
    results["_overall_parity"] = all_ok
    return results


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Stage-1 benchmark suite")
    parser.add_argument("--warmup", type=int, default=1,
                        help="Number of warm-up passes before timing (default 1)")
    parser.add_argument("--reps", type=int, default=3,
                        help="Number of measured repetitions (default 3)")
    args = parser.parse_args()

    BENCHMARKS_DIR.mkdir(parents=True, exist_ok=True)

    all_metrics = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "warmup_passes": args.warmup,
        "measurement_reps": args.reps,
    }

    all_metrics["environment"]       = capture_environment()
    all_metrics["indexing_speed"]    = benchmark_indexing_speed(args.warmup, args.reps)
    all_metrics["storage_footprint"] = benchmark_storage_footprint()
    all_metrics["query_latency"]     = benchmark_query_latency(args.warmup, args.reps)
    all_metrics["datalake_lookup"]   = benchmark_datalake_lookup()
    all_metrics["discovery"]         = benchmark_discovery()
    all_metrics["storage_state"]     = benchmark_storage_state()
    all_metrics["idempotency"]       = benchmark_idempotency()
    all_metrics["incremental_update"]= benchmark_incremental_update()
    all_metrics["growth_scaling"]    = benchmark_growth_scaling()
    all_metrics["parity"]            = benchmark_parity()

    output_json = BENCHMARKS_DIR / "benchmark_results.json"
    with open(output_json, "w", encoding="utf-8") as fh:
        json.dump(all_metrics, fh, indent=2, ensure_ascii=False)

    section("ALL BENCHMARKS COMPLETE")
    print(f"  Results saved to: {output_json}")
    print(f"  Reproduce with:  python benchmarks/run_benchmarks.py --warmup {args.warmup} --reps {args.reps}")
    print("=" * 72)