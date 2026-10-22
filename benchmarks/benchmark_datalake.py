"""
benchmark_datalake.py  –  Datalake layout look-up cost measurement.

Measures the look-up latency for both storage layouts:
  - Time partitioning  (datalake/time/YYYYMMDD/HH/) → O(N) walk
  - ID partitioning    (datalake/id/XX/YY/)          → O(1) direct path
"""

import os
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATALAKE_DIR = BASE_DIR / "datalake"
SAMPLE_DATA_DIR = BASE_DIR / "sample_data"


def benchmark_datalake_lookup(sample_book_id: int | None = None) -> dict:
    """
    Measure look-up cost for the time-partitioned and ID-partitioned layouts.

    Parameters
    ----------
    sample_book_id : int | None
        Book ID to search for.  If None, the first *_body.txt in sample_data
        is used; falls back to ID 6 if sample_data is empty.

    Returns
    -------
    dict with keys ``partition_time_ms`` and ``partition_id_ms``.
    """
    if sample_book_id is None:
        sample_files = (
            list(SAMPLE_DATA_DIR.glob("*_body.txt"))
            if SAMPLE_DATA_DIR.exists()
            else []
        )
        sample_book_id = (
            int(sample_files[0].stem.split("_")[0])
            if sample_files
            else 6
        )

    # ── A) Time-partitioned layout: O(N) recursive walk ──────────────────
    time_dir = DATALAKE_DIR / "time"
    time_cost_ms = 0.0
    if time_dir.exists():
        target_filename = f"{sample_book_id}_body.txt"
        t0 = time.perf_counter()
        found = None
        for root, _, files in os.walk(time_dir):
            if target_filename in files:
                found = Path(root) / target_filename
                break
        time_cost_ms = (time.perf_counter() - t0) * 1000
        status = f"found at {found}" if found else "not found"
        print(f"  [Time-layout] Book {sample_book_id}: {status}  ({time_cost_ms:.4f} ms)")
    else:
        print(f"  [Time-layout] datalake/time/ not present – skipped.")

    # ── B) ID-partitioned layout: O(1) mathematically derived path ───────
    id_dir = DATALAKE_DIR / "id"
    id_cost_ms = 0.0
    id_str = f"{sample_book_id:04d}"
    parts = [id_str[i:i+2] for i in range(0, len(id_str), 2)]
    calculated_path = id_dir
    for part in parts:
        calculated_path = calculated_path / part
    target_file = calculated_path / f"{sample_book_id}_body.txt"

    t0 = time.perf_counter()
    exists = target_file.exists()
    id_cost_ms = (time.perf_counter() - t0) * 1000
    print(f"  [ID-layout]   Book {sample_book_id}: "
          f"{'found' if exists else 'not found'} at {target_file}  ({id_cost_ms:.4f} ms)")

    return {
        "partition_time_ms": round(time_cost_ms, 4),
        "partition_id_ms": round(id_cost_ms, 4),
    }


if __name__ == "__main__":
    results = benchmark_datalake_lookup()
    print("\nResults:", results)