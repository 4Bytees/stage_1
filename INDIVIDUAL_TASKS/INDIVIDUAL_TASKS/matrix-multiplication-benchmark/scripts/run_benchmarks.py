import argparse
import csv
import datetime as dt
from pathlib import Path

import numpy as np

from common import DEFAULT_WARMUP, INPUTS, LANGS, ROOT, run_once

SIZES = {"c": [10, 100, 200, 500, 1000, 1024, 1500, 2000],
         "java": [10, 100, 200, 500, 1000, 1024, 1500, 2000],
         "python": [10, 100, 200, 500, 1000]}
CHECKSUM_RTOL = 1e-10
FIELDS = ["timestamp", "lang", "n", "rep", "dtype", "warmup_runs", "cpu", "timeout_s", "mem_limit_mb",
          "status", "time_s", "peak_mem_mb", "mem_metric", "checksum", "ref_checksum", "checksum_ok",
          "theoretical_mb", "exit_code", "note"]


def reference_checksum(n, cache={}):
    if n not in cache:
        a = np.fromfile(INPUTS / f"A_{n}.bin", dtype="<f8").reshape(n, n)
        b = np.fromfile(INPUTS / f"B_{n}.bin", dtype="<f8").reshape(n, n)
        cache[n] = float((a @ b).sum())
    return cache[n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", nargs="+", default=list(LANGS), choices=LANGS)
    for lang in LANGS:
        ap.add_argument(f"--sizes-{lang}", type=int, nargs="+", default=SIZES[lang])
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--cpu", type=int, default=2, help="logical processor to pin each run to")
    ap.add_argument("--timeout", type=int, default=600, help="seconds per run")
    ap.add_argument("--mem-limit-mb", type=int, default=4096)
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "raw" / "results.csv")
    args = ap.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    new_file = not args.out.exists()
    with open(args.out, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()

        def emit(**row):
            row.setdefault("timestamp", dt.datetime.now().isoformat(timespec="seconds"))
            writer.writerow(row)
            f.flush()

        for lang in args.langs:
            failed_at = None
            for n in getattr(args, f"sizes_{lang}"):
                common = dict(lang=lang, n=n, dtype="float64", warmup_runs=DEFAULT_WARMUP[lang], cpu=args.cpu,
                              timeout_s=args.timeout, mem_limit_mb=args.mem_limit_mb,
                              mem_metric="peak_wset(Windows)/sampled_rss(other), whole process tree",
                              theoretical_mb=round(3 * 8 * n * n / 1e6, 3))
                if failed_at is not None:
                    emit(**common, rep=0, status="skipped", note=f"skipped: n={failed_at} already hit a limit")
                    print(f"{lang:7s} n={n:5d} skipped")
                    continue
                ref = reference_checksum(n)
                for rep in range(1, args.reps + 1):
                    r = run_once(lang, n, DEFAULT_WARMUP[lang], cpu=args.cpu, timeout=args.timeout,
                                 mem_limit_mb=args.mem_limit_mb)
                    ok = None
                    if r["checksum"] is not None:
                        ok = abs(r["checksum"] - ref) <= CHECKSUM_RTOL * abs(ref)
                    emit(**common, rep=rep, status=r["status"], time_s=r["time_s"], peak_mem_mb=r["peak_mb"],
                         checksum=r["checksum"], ref_checksum=ref, checksum_ok=ok, exit_code=r["exit_code"],
                         note=r["stderr"])
                    print(f"{lang:7s} n={n:5d} rep={rep} {r['status']:8s} time={r['time_s']} "
                          f"peak={r['peak_mb']} MB checksum_ok={ok}")
                    if r["status"] != "ok":
                        failed_at = n
                        break


if __name__ == "__main__":
    main()
