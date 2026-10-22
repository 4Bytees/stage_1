import os
import re
import subprocess
import sys
import time
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parent.parent
INPUTS = ROOT / "data" / "inputs"
EXE = ".exe" if os.name == "nt" else ""

LANGS = ("c", "java", "python")
# Warm-up = number of 128x128 multiplications executed before the timed one (see README).
DEFAULT_WARMUP = {"c": 0, "java": 50, "python": 0}
JAVA_FLAGS = ["-Xmx4g", "-XX:+UseSerialGC"]

RESULT_RE = re.compile(r"RESULT time_s=([0-9.eE+-]+) checksum=([0-9.eE+-]+)")


def command(lang, n, warmup, dump=None, inputs=INPUTS):
    if lang == "c":
        cmd = [str(ROOT / "c" / "build" / f"benchmark{EXE}")]
    elif lang == "java":
        cmd = ["java", *JAVA_FLAGS, "-cp", str(ROOT / "java" / "build" / "classes"),
               "matrixbench.Benchmark"]
    elif lang == "python":
        cmd = [sys.executable, str(ROOT / "python" / "src" / "benchmark.py")]
    else:
        raise ValueError(lang)
    cmd += [str(inputs), str(n), str(warmup)]
    if dump:
        cmd.append(str(dump))
    return cmd


def _tree(proc):
    try:
        return [proc] + proc.children(recursive=True)
    except psutil.Error:
        return [proc]


def _peak_bytes(proc):
    """Peak memory of a process tree: max over processes of peak working set (Windows)
    or of the sampled RSS (other systems). max, not sum, so a launcher stub is not double counted."""
    best = 0
    for p in _tree(proc):
        try:
            mi = p.memory_info()
        except psutil.Error:
            continue
        best = max(best, getattr(mi, "peak_wset", 0) or mi.rss)
    return best


def _pin_affinity(cpu):
    """Pin the *orchestrator* to `cpu` while spawning so the child inherits the affinity,
    then move the orchestrator away from `cpu` and its presumed hyper-thread sibling."""
    me = psutil.Process()
    try:
        original = me.cpu_affinity()
        me.cpu_affinity([cpu])
    except (AttributeError, psutil.Error, ValueError):
        return None, None
    return me, original


def _unpin(me, original, cpu):
    if me is None:
        return
    others = [c for c in original if c not in (cpu, cpu ^ 1)] or [c for c in original if c != cpu] or original
    try:
        me.cpu_affinity(others)
    except psutil.Error:
        pass


def run_once(lang, n, warmup, cpu=None, timeout=600, mem_limit_mb=4096, dump=None, poll=0.002):
    """Run one program once in a fresh process. Returns a dict with status, time_s, checksum, peak_mb."""
    cmd = command(lang, n, warmup, dump)
    me, original = _pin_affinity(cpu) if cpu is not None else (None, None)
    try:
        proc = psutil.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    finally:
        if cpu is not None:
            _unpin(me, original, cpu)

    peak = 0
    status = "ok"
    start = time.monotonic()
    out = err = ""
    while True:
        peak = max(peak, _peak_bytes(proc))  # sample first: very short runs may end before a later sample
        try:
            out, err = proc.communicate(timeout=poll)
            break
        except subprocess.TimeoutExpired:
            if time.monotonic() - start > timeout:
                status = "timeout"
            elif peak / 1e6 > mem_limit_mb:
                status = "memlimit"
            if status != "ok":
                for p in _tree(proc):
                    try:
                        p.kill()
                    except psutil.Error:
                        pass
                out, err = proc.communicate()
                break
    # peak == 0 means the process ended before any sample succeeded: report NA, never an invented 0.
    result = {"status": status, "exit_code": proc.returncode, "time_s": None, "checksum": None,
              "peak_mb": round(peak / 1e6, 3) if peak > 0 else None, "stderr": (err or "").strip()[:300]}
    if status == "ok":
        m = RESULT_RE.search(out or "")
        if proc.returncode == 0 and m:
            result["time_s"] = float(m.group(1))
            result["checksum"] = float(m.group(2))
        else:
            result["status"] = "error"
    return result
