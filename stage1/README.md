# Search Engine — Stage 1: Building the Data Layer

**Group:** `4Bytees`

---

## Project Overview

Full implementation of the storage, ingestion, and indexing pipeline for a search engine that processes literature from *Project Gutenberg*. The architecture consists of five core subsystems:

1. **Data Lake** — Raw ingestion engine with two storage-partitioning strategies:
   - **Time Partitioning:** `datalake/time/YYYYMMDD/HH/` (append-friendly, O(N) lookup)
   - **ID Partitioning:** `datalake/id/XX/YY/` (two-digit numeric bucketing, O(1) direct path)

2. **Control Layer** — Idempotent supervisor that tracks downloaded and indexed book IDs in plain-text state files (`control/downloaded_books.txt`, `control/indexed_books.txt`). A book is marked *indexed* **only** if the full metadata + inverted-index pipeline completes without exceptions.

3. **Metadata Extraction** — Regex-based parser extracting `Title`, `Author`, `Language` from book headers, persisted to a relational SQLite database (`datamarts/metadata.db`).

4. **Multilanguage Inverted Indexers** — Symmetric implementations in **Python**, **Java (JDK 21)**, and **C (GCC -O2)**, each enforcing identical lexical tokenisation (29 stop-words, lowercase alphabetic tokens of length ≥ 3). Each language exports three datamart structures:
   - **Monolithic:** single cumulative JSON index (`inverted_index*.json`)
   - **Hierarchical:** partitioned directory tree by initial letter (`inverted_index_folders*/[A-Z]/[term].txt`)
   - **Tabular / Relational:** SQLite (`.db`) or Tab-Separated Values (`.tsv`)

5. **Benchmarking Suite** — Quantitative harness measuring: indexing throughput, storage footprint (logical vs physical), query latency, datalake lookup efficiency, discovery, idempotency, incremental update cost, growth scaling, and cross-language parity.

---

## Repository Structure

```text
stage1/
├── benchmarks/                   # Benchmark orchestrator and exported metrics
│   ├── run_benchmarks.py         # Main benchmark runner (10 experiments)
│   ├── benchmark_datalake.py     # Datalake lookup latency module
│   ├── benchmark_java_query.py   # Java query benchmark invocation wrapper
│   ├── benchmark_results.json    # Last benchmark run output
│   └── metrics.csv               # Condensed CSV for report tables
├── bin/                          # Compiled binaries (Main.class, indexer_c.exe)
├── control/                      # Audit/state files
│   ├── downloaded_books.txt
│   ├── indexed_books.txt
│   └── failed_to_download_books.txt
├── datalake/                     # Raw partitioned data storage
│   ├── time/                     # YYYYMMDD/HH/ layout
│   └── id/                       # XX/YY/ layout
├── datamarts/                    # Inverted-index output structures
│   ├── inverted_index.json       # Python monolithic
│   ├── inverted_index_folders/   # Python hierarchical
│   ├── inverted_index.db         # Python relational (SQLite)
│   ├── inverted_index_java.json  # Java monolithic
│   ├── inverted_index_folders_java/
│   ├── inverted_index_java.tsv   # Java tabular
│   ├── inverted_index_c.json     # C monolithic
│   ├── inverted_index_folders_c/
│   ├── inverted_index_c.tsv      # C tabular
│   └── metadata.db               # Book metadata (title, author, language)
├── sample_data/                  # Local test corpus (*_header.txt, *_body.txt)
├── src/
│   ├── C/                        # C native indexing engine
│   │   ├── main.c
│   │   └── Makefile
│   ├── java/                     # Java indexing module (production only)
│   │   ├── Main.java
│   │   └── indexer/
│   │       ├── BaseContainer.java
│   │       ├── MonolithicIndexer.java
│   │       ├── HierarchicalIndexer.java
│   │       └── TsvIndexer.java
│   └── python/                   # Crawler, storage adapters, control layer, indexer
│       ├── main.py               # Pipeline entry point
│       ├── control_layer.py      # ControlLayer supervisor
│       ├── crawler_controller.py # HTTP download engine
│       ├── gutenberg_request.py  # Gutenberg HTTP client
│       ├── tokenizer.py          # Standalone tokenizer utility
│       ├── query_benchmark.py    # Query helpers (mono / hierarchical / SQLite)
│       ├── indexer/
│       │   ├── base_container.py
│       │   ├── indexer.py
│       │   └── containers/
│       │       ├── monolithic_indexer.py
│       │       ├── hierarchical_indexer.py
│       │       └── sqlite_indexer.py
│       ├── metadata/
│       │   └── metadata_parser.py
│       └── storage/
│           ├── book_storage.py
│           ├── book_storage_date.py
│           └── book_storage_id.py
└── requirements.txt
```

---

## Prerequisites

| Component | Requirement |
|-----------|-------------|
| Python    | ≥ 3.11      |
| Java      | JDK 21+     |
| C compiler| GCC ≥ 12 (MinGW on Windows) |

```bash
pip install -r requirements.txt
```

> `psutil` is optional (used only for RAM capture in benchmarks).  
> `requests` is optional (only needed for live HTTP crawling; not required for `sample_data` experiments).

---

## Step-by-Step Execution

### 1. Run the full pipeline (download + index a range of books)

```bash
cd stage1/
python src/python/main.py --start 1 --end 6
```

This will:
1. Download books 1–6 from Project Gutenberg into `datalake/time/`.
2. Extract metadata → `datamarts/metadata.db`.
3. Build all three inverted-index structures → `datamarts/`.

### 2. Run the Python indexer standalone (on `sample_data/`)

```bash
cd stage1/
python src/python/indexer/indexer.py
```

### 3. Compile and run the Java indexer

```bash
cd stage1/
mkdir -p bin
javac -d bin src/java/*.java src/java/indexer/*.java
java -cp bin Main sample_data
```

### 4. Compile and run the C indexer

**Linux / macOS:**
```bash
cd stage1/
gcc -O2 -o bin/indexer_c src/C/main.c
bin/indexer_c sample_data
```

**Windows (MinGW):**
```powershell
cd stage1
gcc -O2 -o bin\indexer_c.exe src\C\main.c
bin\indexer_c.exe sample_data
```

### 5. Run the full benchmark suite

```bash
cd stage1/
python benchmarks/run_benchmarks.py --warmup 1 --reps 3
```

Results are saved to `benchmarks/benchmark_results.json`.

To reproduce the exact tables from the report:
```bash
python benchmarks/run_benchmarks.py --warmup 2 --reps 5
```

---

## Benchmark Experiments

| # | Experiment | Key Metric |
|---|-----------|-----------|
| 1 | Indexing speed by language | mean ms ± stddev |
| 2 | Storage footprint | logical KB vs physical KB |
| 3 | Query latency by structure | ms/term |
| 4 | Datalake lookup cost | ms (O(N) walk vs O(1) direct) |
| 5 | Discovery (pending books) | discovery latency ms |
| 6 | Storage state metadata | file/dir counts per structure |
| 7 | Idempotency / interruption | MD5 comparison of two runs |
| 8 | Incremental update cost | ms and KB delta |
| 9 | Growth scaling | time × corpus size |
| 10 | Cross-language parity | posting-set equality check |

---

## Posting File Line Format

All three languages use the **same line format** in hierarchical `.txt` posting files:

```
<book_id>,<frequency>,[<pos1>, <pos2>, ...]
```

Example: `6,14,[3, 17, 42, 91, 134, 210, 305, 400, 512, 600, 710, 850, 900, 1024]`

---

## Known Limitations

- All experiments were run on a **6-book corpus** (`sample_data/`). Observed rankings (speed, storage) may not generalise to large-scale corpora.
- The C monolithic JSON output (`inverted_index_c.json`) is produced at the **end** of processing (not incrementally per book); parity with Python/Java is verified post-run.
- Java `QueryBenchmark.java` has been relocated from `src/java/indexer/` to `benchmarks/` so that the production source tree contains only indexing logic.
