import time
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
SAMPLE_DIR = BASE_DIR / "sample_data"
TEST_DL = BASE_DIR / "datalake_test"

def benchmark_datalake_structures():
    books = list(SAMPLE_DIR.glob("*_body.txt"))
    if not books:
        print("[!]Dont find books in sample_data")
        return

    time_dir = TEST_DL / "time_based" / "20261004" / "12"
    time_dir.mkdir(parents=True, exist_ok=True)
    
    t0 = time.perf_counter()
    for b in books:
        shutil.copy(b, time_dir / b.name)
    write_time_based = time.perf_counter() - t0

    book_dir = TEST_DL / "book_based"
    book_dir.mkdir(parents=True, exist_ok=True)
    
    t0 = time.perf_counter()
    for b in books:
        book_id = b.name.split("_")[0]
        sub = book_dir / book_id
        sub.mkdir(exist_ok=True)
        shutil.copy(b, sub / "body.txt")
    write_book_based = time.perf_counter() - t0

    target_id = books[0].name.split("_")[0]
    
    t0 = time.perf_counter()
    _ = list((TEST_DL / "time_based").rglob(f"{target_id}_body.txt"))
    lookup_time_based = time.perf_counter() - t0

    t0 = time.perf_counter()
    _ = (TEST_DL / "book_based" / target_id / "body.txt").exists()
    lookup_book_based = time.perf_counter() - t0

    shutil.rmtree(TEST_DL, ignore_errors=True)

    print("\n=== RESULTS BENCHMARK DATALAKE (Requisito 3.1) ===")
    print(f"Time-Based Write Time : {write_time_based*1000:.2f} ms | Lookup (Scan) : {lookup_time_based*1000:.3f} ms")
    print(f"Book-Based Write Time : {write_book_based*1000:.2f} ms | Lookup (Direct): {lookup_book_based*1000:.3f} ms")