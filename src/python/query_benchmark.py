from pathlib import Path
import statistics
import time

from indexer.inverted_index_store import (
    HierarchicalIndexStore,
    MonolithicIndexStore,
    SqliteIndexStore,
)


BASE_DIR = Path(__file__).resolve().parents[2]
DATAMARTS_DIR = BASE_DIR / "datamarts"


def create_stores(datamarts_dir=DATAMARTS_DIR):
    root = Path(datamarts_dir)

    return {
        "monolithic": MonolithicIndexStore(
            root / "inverted_index.json"
        ),
        "hierarchical": HierarchicalIndexStore(
            root / "inverted_index_folders"
        ),
        "sqlite": SqliteIndexStore(
            root / "inverted_index.db"
        ),
    }


# Funciones conservadas para llamadas existentes.
# Cada llamada independiente construye su lector.
def query_monolithic(term: str, datamarts_dir=DATAMARTS_DIR) -> list[dict]:
    return MonolithicIndexStore(
        Path(datamarts_dir) / "inverted_index.json"
    ).query(term)


def query_hierarchical(term: str, datamarts_dir=DATAMARTS_DIR) -> list[dict]:
    return HierarchicalIndexStore(
        Path(datamarts_dir) / "inverted_index_folders"
    ).query(term)


def query_sqlite(term: str, datamarts_dir=DATAMARTS_DIR) -> list[dict]:
    return SqliteIndexStore(
        Path(datamarts_dir) / "inverted_index.db"
    ).query(term)


def run_query_benchmarks(
    terms: list[str],
    datamarts_dir=DATAMARTS_DIR,
    repeats: int = 10,
    warmups: int = 2,
) -> dict:
    """
    Mediana de consultas repetidas tras calentamiento.

    La construccion de los lectores queda fuera del tiempo medido:
    - JSON: consulta sobre un indice ya cargado en memoria.
    - Jerarquico: lectura y parseo del archivo de termino.
    - SQLite: apertura, consulta, parseo y cierre de conexion.

    No es una medicion de disco frio ni de carga inicial.
    """
    if repeats < 1 or warmups < 0:
        raise ValueError("repeats debe ser >= 1 y warmups >= 0.")

    stores = create_stores(datamarts_dir)
    results = {}

    count_keys = {
        "monolithic": "postings_count_mono",
        "hierarchical": "postings_count_hier",
        "sqlite": "postings_count_sqlite",
    }

    for term in terms:
        metrics = {}

        for name, store in stores.items():
            for _ in range(warmups):
                store.query(term)

            samples = []
            postings = []

            for _ in range(repeats):
                start = time.perf_counter_ns()
                postings = store.query(term)
                elapsed_ns = time.perf_counter_ns() - start
                samples.append(elapsed_ns / 1_000_000)

            metrics[f"{name}_ms"] = statistics.median(samples)
            metrics[count_keys[name]] = len(postings)

        results[term] = metrics

    return results


def verify_query_parity(
    terms: list[str],
    datamarts_dir=DATAMARTS_DIR,
) -> dict:
    """
    Compara IDs, frecuencias y posiciones entre los tres indices Python.

    Solo comprueba los terminos recibidos, no todo el vocabulario.
    No comprueba paridad entre lenguajes.
    """
    stores = create_stores(datamarts_dir)
    report = {}

    for term in terms:
        postings = {
            name: store.query(term)
            for name, store in stores.items()
        }

        ok = (
            postings["monolithic"]
            == postings["hierarchical"]
            == postings["sqlite"]
        )

        report[term] = {
            "parity_ok": ok,
            "details": (
                "Coinciden IDs, frecuencias y posiciones."
                if ok
                else "Difieren las entradas completas; consulta postings."
            ),
            "postings": postings,
        }

    return report