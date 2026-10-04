# Stage 1: Data Layer Construction & Benchmarking

[![Project Stage](https://img.shields.io/badge/Stage-1--Data%20Layer-blue.svg)](https://github.com/4Bytees/stage_1)
[![Languages](https://img.shields.io/badge/Languages-Python%20%7C%20Java%20%7C%20C-brightgreen.svg)](#multilingual-implementations)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An end-to-end Big Data acquisition, storage, and indexing pipeline built for the **Project Gutenberg** corpus. This repository represents **Stage 1** of the search engine project, focusing on raw data ingestion (Datalake), structured metadata/index storage (Datamarts), control orchestration, and comparative performance benchmarking across 3 programming languages (Python, Java, and C) and multiple index structures.

---

## 📌 Table of Contents
- [Architecture Overview](#-architecture-overview)
- [Repository Structure](#-repository-structure)
- [Key Features](#-key-features)
- [Multilingual Implementations](#-multilingual-implementations)
- [Benchmark & Experimental Setup](#-benchmark--experimental-setup)
- [Getting Started](#-getting-started)
- [Execution & Usage](#-execution--usage)
- [Data Retention & .gitignore Policy](#-data-retention--gitignore-policy)

---

## 🏗️ Architecture Overview

The pipeline strictly adheres to a modular Big Data processing architecture:

1. **Crawler / Ingestion Layer**: Fetches raw eBooks from Project Gutenberg by ID, splitting the raw stream into metadata headers (`.header.txt`) and clean content bodies (`.body.txt`).
2. **Datalake (Unstructured Storage)**: Organizes ingested files locally using time-hierarchical structures or standard raw partitions.
3. **Datamarts (Structured Storage)**:
   - **Metadata Mart**: Parses header files to extract attributes (*Title, Author, Release Date, Language*) into an SQLite relational store (`metadata.db`).
   - **Inverted Index Mart**: Tokenizes and normalizes clean book bodies (filtering punctuation, numbers, and multilingual stop words) to build inverted index representations.
4. **Control Layer**: Manages execution state through tracker files (`downloaded_books.txt`, `indexed_books.txt`) to ensure idempotency and prevent duplicate processing.

---

## 📂 Repository Structure

```text
stage_1/
├── .gitignore                      # Git exclusion rules for heavy datalake/datamart files
├── README.md                       # Project documentation
├── requirements.txt                # Python environment dependencies
│
├── src/                            # Source code modules
│   ├── python/                     # Core Python pipeline
│   │   ├── crawler/                # Downloader & header/body parser
│   │   ├── metadata/               # Metadata extractor & SQLite writer
│   │   ├── indexer/                # Multilingual tokenizer & inverted index builder
│   │   ├── control_layer.py        # Pipeline execution orchestrator
│   │   └── main.py                 # Main entry point
│   │
│   ├── java/                       # Java pipeline implementation
│   │   └── ...                     # Ingestion & indexer classes
│   │
│   └── c/                          # C language high-performance indexer
│       └── ...                     # C tokenization & index binaries
│
├── benchmarks/                     # Performance benchmarking suite
│   ├── benchmark_runner.py         # Metrics collector (Time & RAM usage)
│   ├── generate_plots.py           # Plotting script for PDF report visuals
│   ├── metrics.csv                 # Consolidated benchmark results
│   └── benchmark_comparison.png    # Exported comparative benchmark charts
│
├── control/                        # Orchestration tracking files
│   ├── .gitkeep
│   ├── downloaded_books.txt
│   └── indexed_books.txt
│
├── sample_data/                    # Small dataset sample for verification
│   ├── 11.header.txt
│   └── 11.body.txt
│
├── datalake/                       # Local raw text storage (Ignored by Git)
│   └── .gitkeep
│
└── datamarts/                      # Local index & database outputs (Ignored by Git)
    └── .gitkeep

```

---

## ✨ Key Features

* **Multilingual Tokenization**: Custom normalization pipeline supporting English, Spanish, and major European languages (lowercasing, accent stripping, stop-word removal).
* **Multiple Index Formats**:
* **Monolithic JSON**: Single aggregate document mapping terms to postings.
* **Hierarchical Directory Tree**: Folder/file-per-letter/term distribution for scalable file-system lookups.
* **Relational/SQLite Store**: Structured metadata storage for fast SQL querying.


* **Robust Control Layer**: State-aware processing preventing redundant downloads or re-indexing.
* **Benchmarking Suite**: Built-in automated tools tracking execution time and peak memory footprint across batch sizes.

---

## 💻 Multilingual Implementations

To evaluate language efficiency and execution overhead, the core processing tasks are implemented in **3 languages**:

* **Python**: Primary rapid-prototyping pipeline and orchestration framework.
* **Java**: High-concurrency Object-Oriented processing engine.
* **C**: Native compiled implementation for zero-overhead tokenization and raw disk IO performance.

---

## 📊 Benchmark & Experimental Setup

The benchmarking suite measures and compares:

1. **Language Performance**: Benchmark execution speed and RAM utilization across Python, Java, and C for identical book sets.
2. **Inverted Index Formats**: Comparative latency and storage cost between Monolithic JSON files and Hierarchical folder indexes.

Metrics are automatically captured in `benchmarks/metrics.csv` and visualized using `benchmarks/generate_plots.py`.

---

## 🚀 Getting Started

### Prerequisites

* **Python**: 3.9 or higher
* **Java**: JDK 11+ (if compiling/running Java modules)
* **GCC / Clang**: For compiling C source files

### Installation

1. Clone this repository:
```bash
git clone [https://github.com/4Bytees/stage_1.git](https://github.com/4Bytees/stage_1.git)
cd stage_1

```


2. (Optional) Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

```


3. Install Python dependencies:
```bash
pip install -r requirements.txt

```



---

## ⚙️ Execution & Usage

### 1. Run Main Processing Pipeline

To execute the standard crawling, metadata extraction, and indexing workflow:

```bash
python src/python/main.py

```

### 2. Run Benchmarks

To run performance tests and log execution metrics across datasets:

```bash
python benchmarks/benchmark_runner.py

```

### 3. Generate Benchmark Plots

To generate updated performance comparison charts for documentation:

```bash
python benchmarks/generate_plots.py

```

---

## 🛡️ Data Retention & .gitignore Policy

Due to Git storage limits and Big Data best practices:

* **`datalake/`** and **`datamarts/`** contents generated during execution are **excluded from version control** via `.gitignore`.
* Folder integrity is maintained in the repository using `.gitkeep` placeholders.
* A lightweight sample dataset is preserved in **`sample_data/`** to allow immediate evaluation upon cloning.

```


Con esto el repositorio [`https://github.com/4Bytees/stage_1.git`](https://github.com/4Bytees/stage_1.git) quedará con la presentación de la entrega.
