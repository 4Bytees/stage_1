"""
Comparacion reproducible del coste de busqueda en dos layouts:

- time/YYYYMMDD/HH/
- id/XX/YY/

Los dos layouts contienen exactamente los mismos seis libros.
"""

import shutil
import statistics
import time
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLE_DATA_DIR = BASE_DIR / "sample_data"
EXPECTED_BOOK_IDS = [1, 2, 3, 4, 5, 6]


def _validate_corpus() -> list[Path]:
    files = sorted(
        SAMPLE_DATA_DIR.glob("*_body.txt"),
        key=lambda path: int(path.stem.split("_")[0]),
    )

    book_ids = [
        int(path.stem.split("_")[0])
        for path in files
    ]

    if book_ids != EXPECTED_BOOK_IDS:
        raise RuntimeError(
            "El corpus debe contener exactamente los libros "
            f"{EXPECTED_BOOK_IDS}; encontrados: {book_ids}"
        )

    empty_files = [
        path.name
        for path in files
        if path.stat().st_size == 0
    ]

    if empty_files:
        raise RuntimeError(
            "El corpus contiene archivos vacios: "
            + ", ".join(empty_files)
        )

    return files


def _id_path(root: Path, book_id: int) -> Path:
    raw_id = f"{book_id:04d}"

    if len(raw_id) % 2 != 0:
        raw_id = "0" + raw_id

    parts = [
        raw_id[index:index + 2]
        for index in range(0, len(raw_id), 2)
    ]

    path = root / "id"

    for part in parts:
        path = path / part

    return path / f"{book_id}_body.txt"


def _build_layouts(workspace: Path) -> tuple[Path, Path]:
    body_files = _validate_corpus()

    time_root = workspace / "time"
    id_root = workspace / "id"

    for position, source in enumerate(body_files):
        book_id = int(source.stem.split("_")[0])

        date_partition = f"202601{position + 1:02d}"
        hour_partition = f"{position:02d}"

        time_target = (
            time_root
            / date_partition
            / hour_partition
            / source.name
        )

        time_target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copy2(source, time_target)

        id_target = _id_path(workspace, book_id)

        id_target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copy2(source, id_target)

    return time_root, id_root


def _lookup_time_layout(
    time_root: Path,
    book_id: int,
) -> Path | None:
    target_name = f"{book_id}_body.txt"

    for path in time_root.rglob(target_name):
        if path.is_file():
            return path

    return None


def _lookup_id_layout(
    workspace: Path,
    book_id: int,
) -> Path | None:
    target = _id_path(workspace, book_id)

    if target.is_file():
        return target

    return None


def _measure_lookup(
    lookup_function,
    *,
    repetitions: int,
) -> dict:
    samples = []
    found_path = None

    for _ in range(repetitions):
        start_ns = time.perf_counter_ns()
        found_path = lookup_function()

        elapsed_ms = (
            time.perf_counter_ns() - start_ns
        ) / 1_000_000

        if found_path is None:
            raise FileNotFoundError(
                "La busqueda no encontro el libro esperado."
            )

        samples.append(elapsed_ms)

    return {
        "mean_ms": round(
            statistics.fmean(samples),
            6,
        ),
        "median_ms": round(
            statistics.median(samples),
            6,
        ),
        "stddev_ms": round(
            statistics.pstdev(samples)
            if len(samples) > 1
            else 0.0,
            6,
        ),
        "samples_ms": [
            round(sample, 6)
            for sample in samples
        ],
        "found_path": str(found_path),
    }


def benchmark_datalake_lookup(
    sample_book_id: int = 6,
    repetitions: int = 100,
) -> dict:
    if sample_book_id not in EXPECTED_BOOK_IDS:
        raise ValueError(
            f"El libro debe pertenecer a {EXPECTED_BOOK_IDS}."
        )

    if repetitions < 1:
        raise ValueError(
            "repetitions debe ser al menos 1."
        )

    workspace = (
        BASE_DIR
        / "benchmarks"
        / ".tmp"
        / "datalake_lookup"
    )

    if workspace.exists():
        shutil.rmtree(workspace)

    workspace.mkdir(
        parents=True,
        exist_ok=True,
    )

    time_root, id_root = _build_layouts(workspace)

    time_result = _measure_lookup(
        lambda: _lookup_time_layout(
            time_root,
            sample_book_id,
        ),
        repetitions=repetitions,
    )

    id_result = _measure_lookup(
        lambda: _lookup_id_layout(
            workspace,
            sample_book_id,
        ),
        repetitions=repetitions,
    )

    print(
        "  [Time layout] "
        f"mean={time_result['mean_ms']:.6f} ms | "
        f"median={time_result['median_ms']:.6f} ms"
    )

    print(
        "  [ID layout]   "
        f"mean={id_result['mean_ms']:.6f} ms | "
        f"median={id_result['median_ms']:.6f} ms"
    )

    return {
        "book_id": sample_book_id,
        "repetitions": repetitions,
        "corpus_book_ids": EXPECTED_BOOK_IDS,
        "time_layout": time_result,
        "id_layout": id_result,
        "layout_paths": {
            "time": str(
                time_root.relative_to(BASE_DIR)
            ),
            "id": str(
                id_root.relative_to(BASE_DIR)
            ),
        },
        "methodology": (
            "Los dos layouts se construyen en un espacio temporal "
            "nuevo con los mismos seis libros. El layout temporal "
            "se busca recursivamente y el layout por ID mediante "
            "una ruta calculada directamente."
        ),
    }


if __name__ == "__main__":
    result = benchmark_datalake_lookup()
    print(result)