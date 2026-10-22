import argparse
import tempfile
from pathlib import Path

import numpy as np

from common import DEFAULT_WARMUP, INPUTS, LANGS, run_once

RTOL = 1e-10


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", type=int, nargs="+", default=[10, 100, 200])
    ap.add_argument("--langs", nargs="+", default=list(LANGS), choices=LANGS)
    args = ap.parse_args()

    ok_all = True
    with tempfile.TemporaryDirectory() as tmp:
        for n in args.sizes:
            a = np.fromfile(INPUTS / f"A_{n}.bin", dtype="<f8").reshape(n, n)
            b = np.fromfile(INPUTS / f"B_{n}.bin", dtype="<f8").reshape(n, n)
            ref = a @ b
            results = {}
            for lang in args.langs:
                dump = Path(tmp) / f"{lang}_{n}.bin"
                r = run_once(lang, n, DEFAULT_WARMUP[lang], dump=dump)
                if r["status"] != "ok":
                    print(f"n={n:5d} {lang:7s} FAILED: {r['status']} {r['stderr']}")
                    ok_all = False
                    continue
                c = np.fromfile(dump, dtype="<f8").reshape(n, n)
                results[lang] = c
                max_rel = float(np.max(np.abs(c - ref) / np.abs(ref)))
                good = max_rel <= RTOL
                ok_all &= good
                print(f"n={n:5d} {lang:7s} max relative error vs NumPy = {max_rel:.2e}  {'OK' if good else 'FAIL'}")
            langs = list(results)
            for other in langs[1:]:
                same = np.array_equal(results[langs[0]], results[other])
                print(f"n={n:5d} bitwise identical {langs[0]} vs {other}: {same}")
    print("\nVALIDATION", "PASSED" if ok_all else "FAILED")
    raise SystemExit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
