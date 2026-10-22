# Basic Matrix Multiplication in Python, Java and C

Big Data · Individual Assignment 1 · 2026-2027 · Universidad de Las Palmas de Gran Canaria

**Research question.** How do runtime and peak memory of the naive O(n³) triple-loop matrix
multiplication grow with matrix size *n* in CPython, Java (OpenJDK) and C (gcc -O3), when all three
multiply the same input matrices under a documented environment?

> Status: skeleton. Report, results and analysis scripts are added in later steps.

## Requirements

| Tool | Version used | Notes |
|---|---|---|
| gcc | _fill in_ | MinGW-w64 / MSYS2 / WinLibs on Windows |
| JDK | _fill in_ (Temurin 11) | `javac` and `java` on PATH |
| Python | 3.13 | packages: `numpy`, `psutil` (analysis step adds `pandas`, `matplotlib`) |

Full hardware/software description: see `ENVIRONMENT.md`.

## Repository layout

```
c/src, c/test            C implementation, benchmark driver, known-answer tests
java/src/main, src/test  Java implementation, benchmark driver, known-answer tests
python/src, python/test  Python implementation, benchmark driver, known-answer tests
scripts/                 generate_inputs, build_all, validate, run_benchmarks (+ common helpers)
data/inputs              shared input matrices (generated, not committed; manifest.json has SHA-256)
data/raw                 raw measurements, one CSV row per repetition
results/, report/        tables, figures and the PDF report (later steps)
```

## Reproduce (run from the repository root)

```powershell
pip install numpy psutil
python scripts/generate_inputs.py                 # shared inputs, fixed seed
python scripts/build_all.py --test                # compile C + Java, run all known-answer tests
python scripts/validate.py                        # compare every language with NumPy (and with each other)
python scripts/run_benchmarks.py --reps 5 --cpu 2 # full campaign -> data/raw/results.csv
```

## Experimental protocol (summary)

* **Algorithm.** i-j-k triple loop, `double` (float64), local accumulator `sum`, products added in order
  k = 0..n-1. No library multiplication in the implementations (NumPy is used only as a correctness reference).
* **Storage.** C: one contiguous row-major `double*`. Java: `double[][]`. Python: list of lists of `float`.
  These differences are inherent to each language and are discussed in the report.
* **Inputs.** `A_n.bin`, `B_n.bin` generated once with NumPy (`default_rng([seed, n, which])`), float64
  little-endian in [0, 1). All languages read the same files.
* **Timed region.** One call to `multiply()`, *including* allocation of the result matrix. Excluded: reading
  inputs, warm-up, checksum, optional dump. Timers: `QueryPerformanceCounter`/`CLOCK_MONOTONIC` (C),
  `System.nanoTime` (Java), `time.perf_counter` (Python).
* **Warm-up.** C and Python: none. Java: 50 multiplications of a 128×128 matrix before the timed run
  (JIT compilation). Warm-up is never part of the reported samples.
* **Isolation.** One fresh process per (language, n, repetition), pinned to one logical processor
  (`--cpu`). Java runs with `-Xmx4g -XX:+UseSerialGC` (single-threaded GC, so no helper threads).
* **Memory metric.** Peak working set of the whole process (Windows `peak_wset` via psutil), sampled from
  outside every 2 ms; includes runtime baseline, input loading and result. For very short runs the process
  can exit before any sample is taken; the value is then stored as empty (NA), never as 0.
  The theoretical array storage `3·8·n²` bytes is stored next to it for reference.
* **Correctness.** Known-answer tests (2×2, 1×1, identity, zero, non-commutativity) per language;
  elementwise comparison with NumPy (relative tolerance 1e-10, justified in `scripts/validate.py`);
  every benchmark run also compares its result checksum with a NumPy reference.
* **Budgets.** Timeout 600 s and memory limit 4096 MB per run. A run that exceeds a limit is recorded with
  its status; larger sizes of that language are recorded as `skipped`. No time is ever invented.
* **Repetitions.** 5 per configuration (raw values kept; median and IQR are computed in the analysis step).
