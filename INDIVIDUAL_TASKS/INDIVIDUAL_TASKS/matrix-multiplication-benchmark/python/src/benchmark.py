
import os
import sys
import time
from array import array

from basic_matrix_multiplier import checksum, multiply

WARMUP_N = 128


def read_matrix(path, n):
    flat = array("d")
    with open(path, "rb") as f:
        flat.fromfile(f, n * n)
    if sys.byteorder != "little":
        flat.byteswap()
    return [flat[i * n:(i + 1) * n].tolist() for i in range(n)]


def warmup_matrix(n, salt):
    return [[((i * 31 + j * 17 + salt) % 100) / 100.0 for j in range(n)] for i in range(n)]


def main():
    if len(sys.argv) < 4:
        sys.stderr.write("usage: benchmark.py <input_dir> <n> <warmup> [dump_file]\n")
        return 1
    directory, n, warmup = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    dump = sys.argv[4] if len(sys.argv) > 4 else None

    a = read_matrix(os.path.join(directory, f"A_{n}.bin"), n)
    b = read_matrix(os.path.join(directory, f"B_{n}.bin"), n)

    sink = 0.0
    if warmup > 0:
        wa, wb = warmup_matrix(WARMUP_N, 1), warmup_matrix(WARMUP_N, 7)
        for _ in range(warmup):
            sink += checksum(multiply(wa, wb))

    t0 = time.perf_counter()
    c = multiply(a, b)
    t1 = time.perf_counter()

    cs = checksum(c)
    if dump:
        out = array("d")
        for row in c:
            out.extend(row)
        if sys.byteorder != "little":
            out.byteswap()
        with open(dump, "wb") as f:
            out.tofile(f)
    print(f"RESULT time_s={t1 - t0:.9f} checksum={cs:.17g}")
    if sink < 0:
        sys.stderr.write(f"{sink}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
