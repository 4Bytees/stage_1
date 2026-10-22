import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

SEED = 20261012
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SIZES = [10, 100, 200, 500, 1000, 1024, 1500, 2000]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sizes", type=int, nargs="+", default=DEFAULT_SIZES)
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "inputs")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    manifest_path = args.out / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    manifest.update({
        "generator": "numpy.random.default_rng([seed, n, which]).random((n, n))",
        "seed": SEED,
        "dtype": "float64 little-endian, row-major",
        "value_range": "[0, 1)",
        "numpy_version": np.__version__,
    })
    files = manifest.setdefault("files", {})

    for n in args.sizes:
        for which, name in enumerate(("A", "B")):
            rng = np.random.default_rng([SEED, n, which])
            m = rng.random((n, n)).astype("<f8")
            path = args.out / f"{name}_{n}.bin"
            m.tofile(path)
            files[path.name] = sha256(path)
            print(f"wrote {path.name}  ({path.stat().st_size / 1e6:.1f} MB)")
    manifest_path.write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
