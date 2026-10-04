# Search Engine - Stage 1: Building the Data Layer

**Group:** `4Bytees`  

---

## Project Overview

Comprehensive implementation of the storage, ingestion, and indexing pipeline for a search engine processing literature from *Project Gutenberg*. The architecture consists of five core subsystems:

1. **Data Lake**: Raw ingestion engine featuring two storage partitioning strategies:
   - **Time Partitioning**: `datalake/time/YYYYMMDD/HH/`
   - **ID Partitioning**: `datalake/id/XX/YY/` (two-digit numeric bucketing)
2. **Control Layer**: An idempotent supervisor that tracks downloaded and indexed resources via state files in `control/` to prevent duplicate processing.
3. **Metadata Extraction**: Regular expression parser extracting book headers (title, author, language) with persistent relational storage in SQLite (`datamarts/metadata.db`).
4. **Multilanguage Inverted Indexers**: Symmetric implementations in **Python**, **Java (JDK 21)**, and **C (GCC)** enforcing identical lexical tokenization (29 stop words, lowercase alphabetic tokens with length $\ge 3$). Each language exports three datamart structures:
   - **Monolithic**: Single cumulative JSON index (`inverted_index*.json`).
   - **Hierarchical**: Partitioned directory tree by initial letter and term files (`inverted_index_folders*/[A-Z]/[term].txt`).
   - **Tabular / Relational**: SQLite database (`.db`) or Tab-Separated Values (`.tsv`).
5. **Benchmarking Suite**: Quantitative harness measuring indexing throughput, storage footprint, query latency, and data lake lookup efficiency.

---

## Repository Structure

```text
stage_1/
├── benchmarks/              # Benchmark orchestrator and exported metrics (JSON)
├── bin/                     # Compiled binaries (.class, .exe)
├── control/                 # Audit logs (downloaded_books.txt, indexed_books.txt)
├── datalake/                # Raw partitioned data storage (time/ and id/)
├── datamarts/               # Output inverted indexes (JSON, Folders, SQLite, TSV)
├── sample_data/             # Local testing corpus (*_header.txt, *_body.txt)
└── src/
    ├── C/                   # C native indexing engine (main.c, Makefile)
    ├── java/                # Java indexing module (Main.java, indexer package)
    └── python/              # Crawler, storage adapters, control layer, and indexer
