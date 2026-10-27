#!/usr/bin/env python3
"""Пропускная способность MACHINE-1 на рекурсивном цикле (план Ф3: не меньше 300 тыс. переходов/с, уровень L2).

  python3 ref/bench/bench_machine.py
"""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from bagaev_ref.machine import cek  # noqa: E402
from bagaev_ref.machine.runner import find_entry, prepare  # noqa: E402


def measure() -> dict:
    project, prog, pre = prepare([("main.bag", (HERE / "loop.bag").read_bytes())])
    info, _ = find_entry(project, "main.main")
    start = time.perf_counter()
    ex = cek.run(prog.functions[info].body, None, 10**9)
    dt = time.perf_counter() - start
    return {"outcome": ex.termination, "value": ex.value, "steps": ex.steps, "seconds": round(dt, 3),
            "transitions_per_second": int(ex.steps / dt)}


if __name__ == "__main__":
    print(json.dumps(measure(), ensure_ascii=False))
