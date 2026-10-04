import time
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATAMARTS_DIR = BASE_DIR / "datamarts"

def query_monolithic(term: str) -> list:
    json_path = DATAMARTS_DIR / "inverted_index.json"
    if not json_path.exists():
        return []
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get(term.lower(), [])

def query_hierarchical(term: str) -> list:
    term = term.lower()
    first_char = term[0].upper() if term[0].isalpha() else "_"
    file_path = DATAMARTS_DIR / "inverted_index_folders" / first_char / f"{term}.txt"
    if not file_path.exists():
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        return [int(line.strip()) for line in f if line.strip().isdigit()]

def run_query_benchmarks(terms: list):
    results = {}
    for term in terms:
        t0 = time.perf_counter()
        postings_mono = query_monolithic(term)
        t_mono = (time.perf_counter() - t0) * 1000  # ms

        t0 = time.perf_counter()
        postings_hier = query_hierarchical(term)
        t_hier = (time.perf_counter() - t0) * 1000  # ms

        results[term] = {
            "postings_count": len(postings_mono),
            "monolithic_ms": round(t_mono, 3),
            "hierarchical_ms": round(t_hier, 3)
        }
    return results