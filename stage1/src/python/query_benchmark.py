"""
Query benchmark helpers for the Python inverted-index data marts.

Each query_* function accepts a term and returns the list of book IDs
that contain that term, together with per-book frequency metadata.

Posting-file line format (hierarchical store):
    <book_id>,<frequency>,[<pos1>, <pos2>, ...]
"""

import time
import json
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATAMARTS_DIR = BASE_DIR / "datamarts"


# ---------------------------------------------------------------------------
# Individual query functions
# ---------------------------------------------------------------------------

def query_monolithic(term: str) -> list[dict]:
    """
    Look up *term* in the monolithic JSON index loaded into RAM.

    Returns a list of dicts with keys ``book_id``, ``frequency``, ``positions``.
    """
    json_path = DATAMARTS_DIR / "inverted_index.json"
    if not json_path.exists():
        return []
    with open(json_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    raw = data.get(term.lower(), {})
    if not raw:
        return []
    return [
        {"book_id": int(bid), "frequency": v["frequency"], "positions": v["positions"]}
        for bid, v in raw.items()
    ]


def query_hierarchical(term: str) -> list[dict]:
    """
    Look up *term* in the hierarchical folder store (one file per term).

    Posting line format: ``<book_id>,<frequency>,[<p1>, <p2>, ...]``

    Returns a list of dicts with keys ``book_id``, ``frequency``, ``positions``.
    """
    term = term.lower()
    first_char = term[0].upper() if term and term[0].isalpha() else "_"
    file_path = DATAMARTS_DIR / "inverted_index_folders" / first_char / f"{term}.txt"
    if not file_path.exists():
        return []

    results = []
    with open(file_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            # Expected format: book_id,frequency,[p1, p2, ...]
            # Split on the first two commas to isolate book_id and frequency,
            # then treat the remainder as the raw positions string.
            parts = line.split(",", 2)
            if len(parts) < 2:
                continue
            try:
                book_id = int(parts[0])
                frequency = int(parts[1])
                positions_raw = parts[2].strip() if len(parts) > 2 else "[]"
                # Parse positions list: strip brackets and split
                positions_raw = positions_raw.strip("[]")
                positions = (
                    [int(p.strip()) for p in positions_raw.split(",") if p.strip().lstrip("-").isdigit()]
                    if positions_raw
                    else []
                )
                results.append({"book_id": book_id, "frequency": frequency, "positions": positions})
            except (ValueError, IndexError):
                continue
    return results


def query_sqlite(term: str) -> list[dict]:
    """
    Look up *term* in the SQLite B-tree index.

    Returns a list of dicts with keys ``book_id``, ``frequency``, ``positions``.
    """
    db_path = DATAMARTS_DIR / "inverted_index.db"
    if not db_path.exists():
        return []
    results = []
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT book_id, frequency, positions FROM inverted_index WHERE term = ?",
            (term.lower(),)
        )
        for book_id, freq, pos_json in cur.fetchall():
            try:
                positions = json.loads(pos_json)
            except (json.JSONDecodeError, TypeError):
                positions = []
            results.append({"book_id": book_id, "frequency": freq, "positions": positions})
    return results


# ---------------------------------------------------------------------------
# Batch benchmark runner
# ---------------------------------------------------------------------------

def run_query_benchmarks(terms: list[str]) -> dict:
    """
    For each term in *terms*, measure latency (ms) for three query strategies.

    Returns
    -------
    dict
        ``{term: {monolithic_ms, hierarchical_ms, sqlite_ms,
                  postings_count_mono, postings_count_hier, postings_count_sqlite}}``
    """
    results: dict = {}
    for term in terms:
        # Monolithic (JSON loaded into RAM)
        t0 = time.perf_counter()
        postings_mono = query_monolithic(term)
        mono_ms = (time.perf_counter() - t0) * 1000

        # Hierarchical (direct file I/O)
        t0 = time.perf_counter()
        postings_hier = query_hierarchical(term)
        hier_ms = (time.perf_counter() - t0) * 1000

        # Relational (SQLite B-tree)
        t0 = time.perf_counter()
        postings_sqlite = query_sqlite(term)
        sqlite_ms = (time.perf_counter() - t0) * 1000

        results[term] = {
            "monolithic_ms": round(mono_ms, 3),
            "hierarchical_ms": round(hier_ms, 3),
            "sqlite_ms": round(sqlite_ms, 3),
            "postings_count_mono": len(postings_mono),
            "postings_count_hier": len(postings_hier),
            "postings_count_sqlite": len(postings_sqlite),
        }
    return results


# ---------------------------------------------------------------------------
# Parity checker: verifies result sets match across all three stores
# ---------------------------------------------------------------------------

def verify_query_parity(terms: list[str]) -> dict:
    """
    For each term, check that monolithic, hierarchical, and SQLite queries
    return the same set of book IDs.  Used in cross-language parity experiments.

    Returns
    -------
    dict
        ``{term: {"parity_ok": bool, "details": str}}``
    """
    report = {}
    for term in terms:
        mono_ids = {r["book_id"] for r in query_monolithic(term)}
        hier_ids = {r["book_id"] for r in query_hierarchical(term)}
        sqlite_ids = {r["book_id"] for r in query_sqlite(term)}

        ok = (mono_ids == hier_ids == sqlite_ids)
        if not ok:
            diff = (
                f"mono={sorted(mono_ids)} hier={sorted(hier_ids)} "
                f"sqlite={sorted(sqlite_ids)}"
            )
        else:
            diff = f"all agree: {sorted(mono_ids)}"
        report[term] = {"parity_ok": ok, "details": diff}
    return report