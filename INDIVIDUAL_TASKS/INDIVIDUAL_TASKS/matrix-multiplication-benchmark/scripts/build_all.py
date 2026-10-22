import argparse
import subprocess
import sys

from common import EXE, ROOT


def run(cmd, **kw):
    print("+", " ".join(map(str, cmd)))
    subprocess.run(cmd, check=True, **kw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--cc", default="gcc")
    ap.add_argument("--javac", default="javac")
    ap.add_argument("--java-release", default="11", help="value of javac --release (empty string = omit the flag)")
    args = ap.parse_args()

    build_c = ROOT / "c" / "build"
    build_c.mkdir(exist_ok=True)
    run([args.cc, "-O3", "-o", build_c / f"benchmark{EXE}",
         ROOT / "c" / "src" / "benchmark.c", ROOT / "c" / "src" / "basic_matrix_multiplier.c"])
    run([args.cc, "-O0", "-o", build_c / f"test_matrix{EXE}",
         ROOT / "c" / "test" / "test_basic_matrix_multiplier.c",
         ROOT / "c" / "src" / "basic_matrix_multiplier.c"])

    classes = ROOT / "java" / "build" / "classes"
    classes.mkdir(parents=True, exist_ok=True)
    sources = [str(p) for p in (ROOT / "java" / "src").rglob("*.java")]
    javac = args.javac.split()
    release = ["--release", args.java_release] if args.java_release else []
    run([*javac, *release, "-d", classes, *sources])

    if args.test:
        run([build_c / f"test_matrix{EXE}"])
        run(["java", "-cp", classes, "matrixbench.BasicMatrixMultiplierTest"])
        run([sys.executable, ROOT / "python" / "test" / "test_basic_matrix_multiplier.py"])


if __name__ == "__main__":
    main()
