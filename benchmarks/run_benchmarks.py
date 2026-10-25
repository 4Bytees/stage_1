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
import shutil
import statistics
import tempfile

def validate_arguments(warmup: int, reps: int) -> None:
    if warmup < 0:
        raise ValueError("--warmup cannot be negative.")

    if reps < 1:
        raise ValueError("--reps must be at least 1.")


def validate_corpus() -> list[Path]:
    body_files = sorted(
        SAMPLE_DIR.glob("*_body.txt"),
        key=lambda path: int(path.stem.split("_")[0]),
    )

    book_ids = [
        int(path.stem.split("_")[0])
        for path in body_files
    ]

    if book_ids != EXPECTED_BOOK_IDS:
        raise RuntimeError(
            "The corpus must contain exactly the books."
            f"{EXPECTED_BOOK_IDS}; founded: {book_ids}"
        )

    empty_files = [
        str(path)
        for path in body_files
        if path.stat().st_size == 0
    ]

    if empty_files:
        raise RuntimeError(
            "The corpus contains empty files: "
            + ", ".join(empty_files)
        )

    return body_files


def clean_directory(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)

    path.mkdir(parents=True, exist_ok=True)


def run_checked(
    command: list[str],
    *,
    cwd: Path,
    label: str,
    timeout: int = 300,
) -> subprocess.CompletedProcess:
    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"{label} failed with code "
            f"{result.returncode}.\n"
            f"COMANDO: {' '.join(command)}\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )

    return result


def validate_json_index(
    index_path: Path,
    expected_book_ids: list[int] | None = None,
) -> dict:
    if not index_path.is_file():
        raise FileNotFoundError(
            f"The index has not been generated: {index_path}"
        )

    with index_path.open("r", encoding="utf-8") as file:
        index = json.load(file)

    if not isinstance(index, dict):
        raise ValueError(
            f"The index {index_path} does not contain a JSON object."
        )

    books = set()
    posting_count = 0

    for term, postings in index.items():
        if not isinstance(term, str):
            raise ValueError("Non-textual term.")

        if not isinstance(postings, dict):
            raise ValueError(
                f"Invalid postings for {term!r}."
            )

        for raw_book_id, posting in postings.items():
            book_id = int(raw_book_id)
            books.add(book_id)
            posting_count += 1

            if not isinstance(posting, dict):
                raise ValueError(
                    f"Invalid postings for {term!r}, book {book_id}."
                )

            frequency = posting.get("frequency")
            positions = posting.get("positions")

            if not isinstance(positions, list):
                raise ValueError(
                    f"Invalid position for {term!r}, "
                    f"book {book_id}."
                )

            if frequency != len(positions):
                raise ValueError(
                    f"Invalid frecuency for {term!r}, "
                    f"book {book_id}."
                )

            if any(
                type(position) is not int or position < 0
                for position in positions
            ):
                raise ValueError(
                    f"Invalid position for {term!r}, "
                    f"book {book_id}."
                )

            if any(
                previous >= current
                for previous, current in zip(
                    positions,
                    positions[1:],
                )
            ):
                raise ValueError(
                    f"Non-increasing positions for {term!r}, "
                    f"book {book_id}."
                )

    found_books = sorted(books)

    if (
        expected_book_ids is not None
        and found_books != expected_book_ids
    ):
        raise ValueError(
            f"Incorrect books in {index_path}: "
            f"{found_books}; expected: {expected_book_ids}"
        )

    return {
        "term_count": len(index),
        "posting_count": posting_count,
        "book_ids": found_books,
    }


def measure_command(
    command_factory,
    *,
    warmup: int,
    reps: int,
    label: str,
) -> dict:
    validate_arguments(warmup, reps)

    for warmup_number in range(warmup):
        command, cwd, validation = command_factory(
            f"warmup_{warmup_number}"
        )

        run_checked(
            command,
            cwd=cwd,
            label=f"{label} warm-up",
        )

        validation()

    samples = []
    validations = []

    for repetition in range(reps):
        command, cwd, validation = command_factory(
            f"rep_{repetition}"
        )

        start_ns = time.perf_counter_ns()

        run_checked(
            command,
            cwd=cwd,
            label=f"{label} repetition {repetition + 1}",
        )

        elapsed_ms = (
            time.perf_counter_ns() - start_ns
        ) / 1_000_000

        samples.append(elapsed_ms)
        validations.append(validation())

    mean_ms = statistics.fmean(samples)
    median_ms = statistics.median(samples)
    stddev_ms = (
        statistics.pstdev(samples)
        if len(samples) > 1
        else 0.0
    )

    print(
        f"  [{label}] "
        f"mean={mean_ms:.2f} ms | "
        f"median={median_ms:.2f} ms | "
        f"stddev={stddev_ms:.2f} ms"
    )

    return {
        "mean_ms": round(mean_ms, 3),
        "median_ms": round(median_ms, 3),
        "stddev_ms": round(stddev_ms, 3),
        "samples_ms": [
            round(sample, 3)
            for sample in samples
        ],
        "validations": validations,
    }

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
JAVA_MAIN_CLASS = BIN_DIR / "Main.class"

C_BINARY = BIN_DIR / (
    "indexer_c.exe"
    if platform.system() == "Windows"
    else "indexer_c"
)

EXPECTED_BOOK_IDS = [1, 2, 3, 4, 5, 6]

for _p in [SRC_PY_DIR, BENCHMARKS_DIR, BASE_DIR]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

try:
    from query_benchmark import create_stores
except ImportError:
    try:
        from src.python.query_benchmark import create_stores
    except ImportError:
        create_stores = None


try:
    from indexer.indexer import process_single_indexing
except ImportError:
    try:
        from src.python.indexer.indexer import (
            process_single_indexing,
        )
    except ImportError:
        process_single_indexing = None


try:
    from benchmark_datalake import (
        benchmark_datalake_lookup as _bm_datalake,
    )
except ImportError:
    try:
        from benchmarks.benchmark_datalake import (
            benchmark_datalake_lookup as _bm_datalake,
        )
    except ImportError:
        _bm_datalake = None

# ---------------------------------------------------------------------------
# Declared environment (update if running on a different machine)
# ---------------------------------------------------------------------------
DECLARED_ENV = {
    "compiler_flags": {
        "C": "gcc 16.1.0 -O3 -std=c11 -Wall -Wextra -Wpedantic",
        "Java": "OpenJDK 11.0.31 / javac 11.0.31",
        "Python": f"CPython {sys.version}",
    },
    "jvm_settings": "-Xmx512m (passed explicitly to Java benchmark processes)",
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

def benchmark_indexing_speed(
    warmup: int = 1,
    reps: int = 3,
) -> dict:
    section("1. INDEXING SPEED BY LANGUAGE")

    body_files = validate_corpus()
    corpus_bytes = sum(
        path.stat().st_size
        for path in body_files
    )

    print(
        f"  Corpus: {len(body_files)} libros | "
        f"{corpus_bytes / 1024:.2f} KiB"
    )
    print(
        f"  Warm-up: {warmup} | "
        f"Repeticiones: {reps}"
    )

    workspace_root = (
        BENCHMARKS_DIR / ".tmp" / "indexing_speed"
    )

    clean_directory(workspace_root)

    python_launcher = (
        "from pathlib import Path; "
        "from indexer.indexer import "
        "discover_book_ids, process_single_indexing; "
        "corpus=Path(__import__('sys').argv[1]); "
        "output=Path(__import__('sys').argv[2]); "
        "ids=discover_book_ids(corpus); "
        "ok=all(process_single_indexing("
        "book_id,corpus_dir=corpus,output_dir=output"
        ") for book_id in ids); "
        "raise SystemExit(0 if ok else 1)"
    )

    def python_factory(run_name: str):
        run_root = workspace_root / "python" / run_name
        output_dir = run_root / "datamarts"
        clean_directory(run_root)

        command = [
            sys.executable,
            "-c",
            python_launcher,
            str(SAMPLE_DIR.resolve()),
            str(output_dir.resolve()),
        ]

        def validation():
            return validate_json_index(
                output_dir / "inverted_index.json",
                EXPECTED_BOOK_IDS,
            )

        environment = os.environ.copy()
        current_pythonpath = environment.get(
            "PYTHONPATH", ""
        )
        environment["PYTHONPATH"] = os.pathsep.join(
            filter(
                None,
                [
                    str(SRC_PY_DIR.resolve()),
                    current_pythonpath,
                ],
            )
        )

        def run_python_checked():
            result = subprocess.run(
                command,
                cwd=BASE_DIR,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=300,
                env=environment,
            )

            if result.returncode != 0:
                raise RuntimeError(
                    "Python ha fallado.\n"
                    f"STDOUT:\n{result.stdout}\n"
                    f"STDERR:\n{result.stderr}"
                )

        return command, BASE_DIR, validation, run_python_checked

    def measure_python() -> dict:
        validate_arguments(warmup, reps)

        for run_number in range(warmup):
            _, _, validation, execute = python_factory(
                f"warmup_{run_number}"
            )
            execute()
            validation()

        samples = []
        validations = []

        for run_number in range(reps):
            _, _, validation, execute = python_factory(
                f"rep_{run_number}"
            )

            start_ns = time.perf_counter_ns()
            execute()
            elapsed_ms = (
                time.perf_counter_ns() - start_ns
            ) / 1_000_000

            samples.append(elapsed_ms)
            validations.append(validation())

        result = {
            "mean_ms": round(
                statistics.fmean(samples), 3
            ),
            "median_ms": round(
                statistics.median(samples), 3
            ),
            "stddev_ms": round(
                statistics.pstdev(samples)
                if len(samples) > 1
                else 0.0,
                3,
            ),
            "samples_ms": [
                round(sample, 3)
                for sample in samples
            ],
            "validations": validations,
        }

        print(
            "  [Python] "
            f"mean={result['mean_ms']:.2f} ms | "
            f"median={result['median_ms']:.2f} ms | "
            f"stddev={result['stddev_ms']:.2f} ms"
        )

        return result

    def java_factory(run_name: str):
        run_root = workspace_root / "java" / run_name
        clean_directory(run_root)

        command = [
            "java",
            "-Xmx512m",
            "-cp",
            str(BIN_DIR.resolve()),
            "Main",
            str(SAMPLE_DIR.resolve()),
        ]

        def validation():
            return validate_json_index(
                run_root
                / "datamarts"
                / "inverted_index_java.json",
                EXPECTED_BOOK_IDS,
            )

        return command, run_root, validation

    def c_factory(run_name: str):
        run_root = workspace_root / "c" / run_name
        clean_directory(run_root)

        command = [
            str(C_BINARY.resolve()),
            str(SAMPLE_DIR.resolve()),
        ]

        def validation():
            return validate_json_index(
                run_root
                / "datamarts"
                / "inverted_index_c.json",
                EXPECTED_BOOK_IDS,
            )

        return command, run_root, validation

    if not JAVA_MAIN_CLASS.is_file():
        raise FileNotFoundError(
            f"Missing {JAVA_MAIN_CLASS}. Compile the Java code first."
        )

    if not C_BINARY.is_file():
        raise FileNotFoundError(
            f"Missing {C_BINARY}. Compile the C code first."
        )

    results = {
        "corpus_book_ids": EXPECTED_BOOK_IDS,
        "corpus_bytes": corpus_bytes,
        "warmup": warmup,
        "repetitions": reps,
        "Python": measure_python(),
        "Java": measure_command(
            java_factory,
            warmup=warmup,
            reps=reps,
            label="Java",
        ),
        "C": measure_command(
            c_factory,
            warmup=warmup,
            reps=reps,
            label="C",
        ),
    }

    python_mean = results["Python"]["mean_ms"]

    for language in ("Python", "Java", "C"):
        language_mean = results[language]["mean_ms"]

        results[language]["speedup_vs_python"] = round(
            python_mean / max(language_mean, 0.001),
            3,
        )

    return results


# ---------------------------------------------------------------------------
# 2. Storage footprint
# ---------------------------------------------------------------------------

def benchmark_storage_footprint() -> dict:
    section("2. STORAGE FOOTPRINT")

    workspace = BENCHMARKS_DIR / ".tmp" / "indexing_speed"

    python_datamarts = (
        workspace / "python" / "rep_0" / "datamarts"
    )
    java_datamarts = (
        workspace / "java" / "rep_0" / "datamarts"
    )
    c_datamarts = (
        workspace / "c" / "rep_0" / "datamarts"
    )

    required_paths = [
        python_datamarts / "inverted_index.json",
        java_datamarts / "inverted_index_java.json",
        c_datamarts / "inverted_index_c.json",
    ]

    missing = [
        str(path)
        for path in required_paths
        if not path.exists()
    ]

    if missing:
        raise FileNotFoundError(
            "First, you must execute benchmark_indexing_speed(). "
            "These outputs are missing:\n"
            + "\n".join(missing)
        )

    structures = {
        "Python Monolithic JSON":
            python_datamarts / "inverted_index.json",

        "Python Hierarchical":
            python_datamarts / "inverted_index_folders",

        "Python SQLite":
            python_datamarts / "inverted_index.db",

        "Java Monolithic JSON":
            java_datamarts / "inverted_index_java.json",

        "Java Hierarchical":
            java_datamarts / "inverted_index_folders_java",

        "Java TSV":
            java_datamarts / "inverted_index_java.tsv",

        "C Monolithic JSON":
            c_datamarts / "inverted_index_c.json",

        "C Hierarchical":
            c_datamarts / "inverted_index_folders_c",

        "C TSV":
            c_datamarts / "inverted_index_c.tsv",
    }

    results = {}

    print(
        f"  {'Structure':<30} | "
        f"{'Logical KiB':>12} | "
        f"{'physical KiB':>12} | "
        f"{'Files':>8} | "
        f"{'Directories':>11}"
    )
    print("  " + "-" * 84)

    for name, path in structures.items():
        logical = get_logical_size_bytes(path)
        physical = get_physical_size_bytes(path)
        counts = count_files_and_dirs(path)

        result = {
            "path": str(path.relative_to(BASE_DIR)),
            "logical_bytes": logical,
            "logical_kib": round(logical / 1024, 3),
            "physical_bytes": physical,
            "physical_kib": round(physical / 1024, 3),
            "file_count": counts["files"],
            "directory_count": counts["dirs"],
        }

        results[name] = result

        print(
            f"  {name:<30} | "
            f"{result['logical_kib']:>12.3f} | "
            f"{result['physical_kib']:>12.3f} | "
            f"{result['file_count']:>8} | "
            f"{result['directory_count']:>11}"
        )

    return results

# ---------------------------------------------------------------------------
# 3. Query latency
# ---------------------------------------------------------------------------

def benchmark_query_latency(
    warmup: int = 1,
    reps: int = 5,
) -> dict:
    section("3. QUERY LATENCY")

    validate_arguments(warmup, reps)

    if create_stores is None:
        raise RuntimeError(
            "Unable to import create_stores from "
            "query_benchmark.py."
        )

    python_datamarts = (
        BENCHMARKS_DIR
        / ".tmp"
        / "indexing_speed"
        / "python"
        / "rep_0"
        / "datamarts"
    )

    c_datamarts = (
        BENCHMARKS_DIR
        / ".tmp"
        / "indexing_speed"
        / "c"
        / "rep_0"
        / "datamarts"
    )

    required_paths = [
        python_datamarts / "inverted_index.json",
        python_datamarts / "inverted_index_folders",
        python_datamarts / "inverted_index.db",
        c_datamarts / "inverted_index_c.tsv",
    ]

    missing = [
        str(path)
        for path in required_paths
        if not path.exists()
    ]

    if missing:
        raise FileNotFoundError(
            "Indexing experiment outputs are missing:\n"
            + "\n".join(missing)
        )

    stores = create_stores(python_datamarts)

    expected_results = {
        term: stores["monolithic"].query(term)
        for term in TEST_TERMS
    }

    for term in TEST_TERMS:
        hierarchical_result = stores["hierarchical"].query(term)
        sqlite_result = stores["sqlite"].query(term)

        if hierarchical_result != expected_results[term]:
            raise ValueError(
                f"The hierarchical index differs for {term!r}."
            )

        if sqlite_result != expected_results[term]:
            raise ValueError(
                f"The SQLite index differs for {term!r}."
            )

    def query_tsv(term: str) -> list[dict]:
        target = term.lower()
        postings = []
        tsv_path = c_datamarts / "inverted_index_c.tsv"

        with tsv_path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                if not line.strip():
                    continue

                fields = line.rstrip("\n").split("\t", 3)

                if len(fields) != 4:
                    raise ValueError(
                        f"Invalid TSV on the line {line_number}."
                    )

                row_term = fields[0]

                if row_term != target:
                    continue

                book_id = int(fields[1])
                frequency = int(fields[2])
                positions = json.loads(fields[3])

                if frequency != len(positions):
                    raise ValueError(
                        "Incorrect frequency in the TSV for "
                        f"{term!r}, libro {book_id}."
                    )

                if any(
                    type(position) is not int or position < 0
                    for position in positions
                ):
                    raise ValueError(
                        "Invalid positions in the TSV for "
                        f"{term!r}, libro {book_id}."
                    )

                if any(
                    previous >= current
                    for previous, current in zip(
                        positions,
                        positions[1:],
                    )
                ):
                    raise ValueError(
                        "Non-increasing positions in the TSV for "
                        f"{term!r}, libro {book_id}."
                    )

                postings.append({
                    "book_id": book_id,
                    "frequency": frequency,
                    "positions": positions,
                })

        postings.sort(
            key=lambda posting: posting["book_id"]
        )

        return postings

    for term in TEST_TERMS:
        tsv_result = query_tsv(term)

        if tsv_result != expected_results[term]:
            raise ValueError(
                f"El TSV de C difiere para {term!r}."
            )

    query_functions = {
        "Python monolithic JSON in memory":
            stores["monolithic"].query,

        "Python hierarchical direct file":
            stores["hierarchical"].query,

        "Python SQLite":
            stores["sqlite"].query,

        "C TSV sequential scan":
            query_tsv,
    }

    results = {
        "terms": list(TEST_TERMS),
        "warmup": warmup,
        "repetitions": reps,
        "methodology": {
            "monolithic": (
                "JSON loaded before measurement; "
                "Only dictionary lookups are measured."
            ),
            "hierarchical": (
                "Opening and direct reading of the term file."
            ),
            "sqlite": (
                "Opening a read-only connection, query, "
                "parsing and closing."
            ),
            "tsv": (
                "Full sequential scan for a single term "
                "per consultation."
            ),
        },
        "structures": {},
    }

    for label, query_function in query_functions.items():
        for _ in range(warmup):
            for term in TEST_TERMS:
                warmup_result = query_function(term)

                if warmup_result != expected_results[term]:
                    raise ValueError(
                        "Incorrect result during warm-up "
                        f"for {term!r} in {label}."
                    )

        batch_samples = []
        per_query_samples = []

        for _ in range(reps):
            start_batch_ns = time.perf_counter_ns()

            for term in TEST_TERMS:
                start_query_ns = time.perf_counter_ns()
                actual = query_function(term)

                elapsed_query_ms = (
                    time.perf_counter_ns() - start_query_ns
                ) / 1_000_000

                if actual != expected_results[term]:
                    raise ValueError(
                        f"Incorrect result for {term!r} "
                        f"in {label}."
                    )

                per_query_samples.append(elapsed_query_ms)

            elapsed_batch_ms = (
                time.perf_counter_ns() - start_batch_ns
            ) / 1_000_000

            batch_samples.append(elapsed_batch_ms)

            structure_result = {
            "batch_mean_ms": round(
                statistics.fmean(batch_samples),
                6,
            ),
            "batch_median_ms": round(
                statistics.median(batch_samples),
                6,
            ),
            "batch_stddev_ms": round(
                (
                    statistics.pstdev(batch_samples)
                    if len(batch_samples) > 1
                    else 0.0
                ),
                6,
            ),
            "per_query_mean_ms": round(
                statistics.fmean(per_query_samples),
                6,
            ),
            "per_query_median_ms": round(
                statistics.median(per_query_samples),
                6,
            ),
            "batch_samples_ms": [
                round(sample, 6)
                for sample in batch_samples
            ],
            "measured_query_count": len(per_query_samples),
            "postings_by_term": {
                term: len(expected_results[term])
                for term in TEST_TERMS
            },
        }

            results["structures"][label] = structure_result

        print(
            f"  [{label}] "
            f"batch mean="
            f"{structure_result['batch_mean_ms']:.6f} ms | "
            f"per-query mean="
            f"{structure_result['per_query_mean_ms']:.6f} ms"
        )

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

def benchmark_discovery(
    repetitions: int = 100,
) -> dict:
    section("5. DISCOVERY EXPERIMENT")

    if repetitions < 1:
        raise ValueError(
            "repetitions must be at least 1."
        )

    workspace = (
        BENCHMARKS_DIR / ".tmp" / "discovery"
    )

    clean_directory(workspace)

    downloaded_file = (
        workspace / "downloaded_books.txt"
    )

    indexed_file = (
        workspace / "indexed_books.txt"
    )

    failed_file = (
        workspace / "failed_to_download_books.txt"
    )

    downloaded_file.write_text(
        "1\n2\n3\n4\n5\n6\n",
        encoding="utf-8",
    )

    indexed_file.write_text(
        "1\n2\n3\n4\n5\n",
        encoding="utf-8",
    )

    failed_file.write_text(
        "",
        encoding="utf-8",
    )

    samples = []
    pending = []

    for _ in range(repetitions):
        start_ns = time.perf_counter_ns()

        downloaded = read_id_set(downloaded_file)
        indexed = read_id_set(indexed_file)
        pending = sorted(downloaded - indexed)

        elapsed_ms = (
            time.perf_counter_ns() - start_ns
        ) / 1_000_000

        if pending != [6]:
            raise ValueError(
                "Discovery returned an unexpected result: "
                f"{pending}"
            )

        samples.append(elapsed_ms)

    result = {
        "downloaded_ids": [1, 2, 3, 4, 5, 6],
        "indexed_ids": [1, 2, 3, 4, 5],
        "failed_ids": [],
        "pending_ids": pending,
        "repetitions": repetitions,
        "mean_ms": round(
            statistics.fmean(samples),
            6,
        ),
        "median_ms": round(
            statistics.median(samples),
            6,
        ),
        "stddev_ms": round(
            (
                statistics.pstdev(samples)
                if len(samples) > 1
                else 0.0
            ),
            6,
        ),
        "samples_ms": [
            round(sample, 6)
            for sample in samples
        ],
        "methodology": (
            "Temporary control files are used: "
            "Books 1-6 are listed as downloaded and "
            "books 1–5 as indexed. "
            "The long-awaited upcoming book is the 6th one."
        ),
    }

    print(
        f"  Downloaded: {result['downloaded_ids']}"
    )
    print(
        f"  Indexed:   {result['indexed_ids']}"
    )
    print(
        f"  Pending:  {result['pending_ids']}"
    )
    print(
        f"  Meean:       {result['mean_ms']:.6f} ms"
    )

    return result

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

def load_json_index(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(
            f"The JSON index does not exist: {path}"
        )

    with path.open("r", encoding="utf-8") as file:
        index = json.load(file)

    if not isinstance(index, dict):
        raise ValueError(
            f"The index does not contain a JSON object: {path}"
        )

    return index


def copy_corpus(
    destination: Path,
    book_ids: list[int],
) -> None:
    clean_directory(destination)

    for book_id in book_ids:
        source = SAMPLE_DIR / f"{book_id}_body.txt"

        if not source.is_file():
            raise FileNotFoundError(
                f"The book from the corpus is missing: {source}"
            )

        shutil.copy2(
            source,
            destination / source.name,
        )


def build_python_index(
    *,
    corpus_dir: Path,
    output_dir: Path,
    book_ids: list[int],
) -> None:
    clean_directory(output_dir)

    for book_id in book_ids:
        ok = process_single_indexing(
            book_id,
            corpus_dir=corpus_dir,
            output_dir=output_dir,
        )

        if not ok:
            raise RuntimeError(
                f"Python was unable to index the book {book_id}"
            )


def benchmark_idempotency() -> dict:
    section("7. IDEMPOTENCY CHECK")

    workspace = (
        BENCHMARKS_DIR / ".tmp" / "idempotency"
    )
    clean_directory(workspace)

    results = {}

    # ---------------------------------------------------------
    # Python
    # ---------------------------------------------------------
    python_output = workspace / "python" / "datamarts"
    build_python_index(
        corpus_dir=SAMPLE_DIR,
        output_dir=python_output,
        book_ids=EXPECTED_BOOK_IDS,
    )

    python_first = load_json_index(
        python_output / "inverted_index.json"
    )

    for book_id in EXPECTED_BOOK_IDS:
        ok = process_single_indexing(
            book_id,
            corpus_dir=SAMPLE_DIR,
            output_dir=python_output,
        )

        if not ok:
            raise RuntimeError(
                "Python failed during the second indexing"
                f"from the book {book_id}."
            )

    python_second = load_json_index(
        python_output / "inverted_index.json"
    )

    python_ok = python_first == python_second

    results["Python"] = {
        "idempotent": python_ok,
        "term_count_before": len(python_first),
        "term_count_after": len(python_second),
    }

    # ---------------------------------------------------------
    # Java
    # ---------------------------------------------------------
    java_root = workspace / "java"
    clean_directory(java_root)

    java_command = [
        "java",
        "-Xmx512m",
        "-cp",
        str(BIN_DIR.resolve()),
        "Main",
        str(SAMPLE_DIR.resolve()),
    ]

    run_checked(
        java_command,
        cwd=java_root,
        label="Java first execution of idempotency",
    )

    java_path = (
        java_root
        / "datamarts"
        / "inverted_index_java.json"
    )

    java_first = load_json_index(java_path)

    run_checked(
        java_command,
        cwd=java_root,
        label="Java second execution for idempotency",
    )

    java_second = load_json_index(java_path)
    java_ok = java_first == java_second

    results["Java"] = {
        "idempotent": java_ok,
        "term_count_before": len(java_first),
        "term_count_after": len(java_second),
    }

    # ---------------------------------------------------------
    # C
    # ---------------------------------------------------------
    c_root = workspace / "c"
    clean_directory(c_root)

    c_command = [
        str(C_BINARY.resolve()),
        str(SAMPLE_DIR.resolve()),
    ]

    run_checked(
        c_command,
        cwd=c_root,
        label="C first idempotency execution",
    )

    c_path = (
        c_root
        / "datamarts"
        / "inverted_index_c.json"
    )

    c_first = load_json_index(c_path)

    run_checked(
        c_command,
        cwd=c_root,
        label="C second idempotency execution",
    )

    c_second = load_json_index(c_path)
    c_ok = c_first == c_second

    results["C"] = {
        "idempotent": c_ok,
        "term_count_before": len(c_first),
        "term_count_after": len(c_second),
    }

    overall = python_ok and java_ok and c_ok
    results["overall_idempotent"] = overall

    print(
        f"  Python idempotent: {python_ok}"
    )
    print(
        f"  Java idempotent:   {java_ok}"
    )
    print(
        f"  C idempotent:      {c_ok}"
    )
    print(
        f" Global results:   {overall}"
    )

    if not overall:
        raise ValueError(
            "At least one language is not idempotent."
        )

    return results


def benchmark_incremental_update() -> dict:
    section("8. INCREMENTAL UPDATE: BOOKS 1-5 TO 1-6")

    if process_single_indexing is None:
        raise RuntimeError(
            "Could not import process_single_indexing."
        )

    workspace = (
        BENCHMARKS_DIR / ".tmp" / "incremental_update"
    )
    output_dir = workspace / "datamarts"

    clean_directory(workspace)

    for book_id in [1, 2, 3, 4, 5]:
        ok = process_single_indexing(
            book_id,
            corpus_dir=SAMPLE_DIR,
            output_dir=output_dir,
        )

        if not ok:
            raise RuntimeError(
                f"Failure while building the initial state: "
                f"book {book_id}."
            )

    before_validation = validate_json_index(
        output_dir / "inverted_index.json",
        [1, 2, 3, 4, 5],
    )

    before_size = get_logical_size_bytes(
        output_dir / "inverted_index.json"
    )

    start_ns = time.perf_counter_ns()

    update_ok = process_single_indexing(
        6,
        corpus_dir=SAMPLE_DIR,
        output_dir=output_dir,
    )

    elapsed_ms = (
        time.perf_counter_ns() - start_ns
    ) / 1_000_000

    if not update_ok:
        raise RuntimeError(
            "Failure when incrementally incorporating book 6."
        )

    after_validation = validate_json_index(
        output_dir / "inverted_index.json",
        EXPECTED_BOOK_IDS,
    )

    after_size = get_logical_size_bytes(
        output_dir / "inverted_index.json"
    )

    result = {
        "initial_book_ids": [1, 2, 3, 4, 5],
        "added_book_id": 6,
        "final_book_ids": EXPECTED_BOOK_IDS,
        "update_ms": round(elapsed_ms, 3),
        "json_size_before_bytes": before_size,
        "json_size_after_bytes": after_size,
        "json_size_delta_bytes": after_size - before_size,
        "validation_before": before_validation,
        "validation_after": after_validation,
    }

    print(
        f"  Estado inicial: libros 1-5, "
        f"{before_validation['term_count']} terms"
    )
    print(
        f"  Included book: 6"
    )
    print(
        f"  Incremental time: {elapsed_ms:.3f} ms"
    )
    print(
        f"  Final state: books 1-6, "
        f"{after_validation['term_count']} terms"
    )

    return result


def benchmark_growth_scaling() -> dict:
    section("9. GROWTH SCALING")

    if process_single_indexing is None:
        raise RuntimeError(
            "Could not import process_single_indexing."
        )

    workspace = (
        BENCHMARKS_DIR / ".tmp" / "growth_scaling"
    )
    clean_directory(workspace)

    corpus_sizes = [1, 2, 4, 6]
    results = {}

    for corpus_size in corpus_sizes:
        book_ids = EXPECTED_BOOK_IDS[:corpus_size]
        output_dir = (
            workspace
            / f"{corpus_size}_books"
            / "datamarts"
        )

        clean_directory(output_dir)

        start_ns = time.perf_counter_ns()

        for book_id in book_ids:
            ok = process_single_indexing(
                book_id,
                corpus_dir=SAMPLE_DIR,
                output_dir=output_dir,
            )

            if not ok:
                raise RuntimeError(
                    "Failure in the growth experiment "
                    f"for the book {book_id}."
                )

        elapsed_ms = (
            time.perf_counter_ns() - start_ns
        ) / 1_000_000

        validation = validate_json_index(
            output_dir / "inverted_index.json",
            book_ids,
        )

        json_size = get_logical_size_bytes(
            output_dir / "inverted_index.json"
        )

        result = {
            "book_ids": book_ids,
            "book_count": corpus_size,
            "total_indexing_ms": round(
                elapsed_ms,
                3,
            ),
            "json_size_bytes": json_size,
            "term_count": validation["term_count"],
            "posting_count": validation["posting_count"],
        }

        results[str(corpus_size)] = result

        print(
            f"  {corpus_size} books | "
            f"{elapsed_ms:.3f} ms | "
            f"{validation['term_count']} terms | "
            f"{json_size / 1024:.3f} KiB"
        )

    return {
        "corpus_sizes": corpus_sizes,
        "measurements": results,
        "methodology": (
            "Each size is processed within an output directory. "
            "new and empty. Size indices are not reused. "
            "previous."
        ),
    }


def benchmark_parity() -> dict:
    section("10. COMPLETE CROSS-LANGUAGE PARITY")

    workspace = (
        BENCHMARKS_DIR / ".tmp" / "indexing_speed"
    )

    python_path = (
        workspace
        / "python"
        / "rep_0"
        / "datamarts"
        / "inverted_index.json"
    )

    java_path = (
        workspace
        / "java"
        / "rep_0"
        / "datamarts"
        / "inverted_index_java.json"
    )

    c_path = (
        workspace
        / "c"
        / "rep_0"
        / "datamarts"
        / "inverted_index_c.json"
    )

    python_index = load_json_index(python_path)
    java_index = load_json_index(java_path)
    c_index = load_json_index(c_path)

    all_terms = (
        set(python_index)
        | set(java_index)
        | set(c_index)
    )

    missing_in_python = sorted(
        all_terms - set(python_index)
    )
    missing_in_java = sorted(
        all_terms - set(java_index)
    )
    missing_in_c = sorted(
        all_terms - set(c_index)
    )

    mismatched_terms = [
        term
        for term in sorted(all_terms)
        if not (
            python_index.get(term)
            == java_index.get(term)
            == c_index.get(term)
        )
    ]

    parity_ok = (
        not missing_in_python
        and not missing_in_java
        and not missing_in_c
        and not mismatched_terms
    )

    result = {
        "python_term_count": len(python_index),
        "java_term_count": len(java_index),
        "c_term_count": len(c_index),
        "union_term_count": len(all_terms),
        "missing_in_python": missing_in_python,
        "missing_in_java": missing_in_java,
        "missing_in_c": missing_in_c,
        "mismatched_term_count": len(
            mismatched_terms
        ),
        "first_mismatched_terms":
            mismatched_terms[:20],
        "parity_ok": parity_ok,
        "comparison_scope": (
            "Complete vocabulary, book IDs, frequencies "
            "and complete lists of positions."
        ),
    }

    print(
        f"  Python: {len(python_index)} terms"
    )
    print(
        f"  Java:   {len(java_index)} terms"
    )
    print(
        f"  C:      {len(c_index)} terms"
    )
    print(
        f"  Postings different: "
        f"{len(mismatched_terms)}"
    )
    print(
        f"  Full parity: {parity_ok}"
    )

    if not parity_ok:
        raise ValueError(
            "Full parity between languages ​​has failed. "
            f"Initial differences: {mismatched_terms[:20]}"
        )

    return result

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
    all_metrics["datalake_lookup"] = (
        benchmark_datalake_lookup()
    )

    all_metrics["discovery"] = benchmark_discovery()

    all_metrics["storage_state"] = {
        "status": "not_executed",
        "reason": (
            "EComparable storage is measured in "
            "storage_footprint for isolated outputs."
        ),
    }
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