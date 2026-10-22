"""
Wrapper to invoke the Java hierarchical-query benchmark from Python.

This module is kept in benchmarks/ (not in src/java/) because QueryBenchmark
is a measurement tool, not production indexing code.

The Java benchmark reads the hierarchical posting files produced by the Java
indexer and reports query latency for a fixed set of test terms.
"""

import subprocess
import json
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
BIN_DIR  = BASE_DIR / "bin"
DATAMARTS_DIR = BASE_DIR / "datamarts"

TEST_TERMS = ["gutenberg", "project", "electronic", "foundation",
              "states", "united", "life", "time"]


def run_java_query_benchmark() -> dict:
    """
    Invoke the compiled Java QueryBenchmark class and parse its output.

    Returns
    -------
    dict  {term: {"java_postings_count": int, "java_query_ms": float}}
    """
    class_file = BIN_DIR / "QueryBenchmarkRunner.class"
    if not class_file.exists():
        print("[Java Query Benchmark] QueryBenchmarkRunner.class not compiled – skipped.")
        return {}

    cmd = ["java", "-cp", str(BIN_DIR), "QueryBenchmarkRunner",
           str(DATAMARTS_DIR)] + TEST_TERMS
    t0 = time.perf_counter()
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(BASE_DIR))
    elapsed_ms = (time.perf_counter() - t0) * 1000

    print(result.stdout)
    if result.returncode != 0:
        print("[Java Query Benchmark ERROR]", result.stderr)

    return {"total_wall_ms": round(elapsed_ms, 2), "raw_output": result.stdout}


if __name__ == "__main__":
    print(run_java_query_benchmark())
