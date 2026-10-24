import json
from pathlib import Path
import subprocess
import time


BASE_DIR = Path(__file__).resolve().parent.parent
BIN_DIR = BASE_DIR / "bin"
DATAMARTS_DIR = BASE_DIR / "datamarts"

TEST_TERMS = [
    "gutenberg",
    "project",
    "electronic",
    "foundation",
    "states",
    "united",
    "life",
    "time",
]


def run_java_query_benchmark(
    terms=None,
    datamarts_dir=DATAMARTS_DIR,
) -> dict:
    terms = list(TEST_TERMS if terms is None else terms)

    if not terms:
        raise ValueError("Debes indicar al menos un termino.")

    class_file = BIN_DIR / "QueryBenchmark.class"

    if not class_file.is_file():
        raise FileNotFoundError(
            "Falta bin/QueryBenchmark.class. Compila primero "
            "benchmarks/java/QueryBenchmark.java."
        )

    command = [
        "java",
        "-Xmx512m",
        "-cp",
        str(BIN_DIR),
        "QueryBenchmark",
        str(Path(datamarts_dir).resolve()),
        *terms,
    ]

    start = time.perf_counter()

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=BASE_DIR,
        timeout=120,
    )

    elapsed_ms = (time.perf_counter() - start) * 1000

    if result.returncode != 0:
        raise RuntimeError(
            "Fallo del benchmark Java:\n"
            + result.stderr
            + result.stdout
        )

    queries = json.loads(result.stdout)

    if not isinstance(queries, dict):
        raise ValueError("Java no ha devuelto un objeto JSON.")

    return {
        "total_wall_ms": elapsed_ms,
        "queries": queries,
        "raw_output": result.stdout,
    }


if __name__ == "__main__":
    print(json.dumps(
        run_java_query_benchmark(),
        indent=2,
        ensure_ascii=False,
    ))