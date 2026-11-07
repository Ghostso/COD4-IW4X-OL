from __future__ import annotations

"""CORE-009 boundary-observation driver.

Builds and invokes the narrow C# observer in `_core009_observer`, then merges the
per-run CSV artifacts. This driver does not modify the game EXE/DLL files.
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OBSERVER_DIR = ROOT / "_core009_observer"
PROJECT = OBSERVER_DIR / "core009_boundary_observation.csproj"
OBSERVER = OBSERVER_DIR / "bin" / "Release" / "net48" / "core009_boundary_observation.exe"
MERGE = ROOT / "core009_merge_artifacts.py"
KINDS = [
    "runs", "registers", "stack", "state_delta", "module_delta",
    "thread_delta", "commandline_matrix", "contract_matrix",
]


def run(cmd: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=timeout)


def build() -> None:
    result = run(["dotnet", "build", str(PROJECT), "-c", "Release", "-v:m"], 120)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"observer build failed: {result.returncode}")
    if not OBSERVER.is_file():
        raise RuntimeError(f"observer not found: {OBSERVER}")


def copy_artifacts(case: str, repeat: int) -> None:
    for kind in KINDS:
        src = ROOT / f"exe_core009_{kind}.csv"
        dst = ROOT / f"exe_core009_{kind}_{case}_{repeat}.csv"
        if src.is_file():
            shutil.copyfile(src, dst)


def observe(case: str, repeat: int, timeout: int) -> None:
    result = run([str(OBSERVER), f"--case={case}", f"--repeat={repeat}"], timeout)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"observer case {case}/{repeat} failed: {result.returncode}")
    copy_artifacts(case, repeat)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=["A", "B", "C", "D"], action="append")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--skip-build", action="store_true")
    args = parser.parse_args()
    if not args.skip_build:
        build()
    cases = args.case or ["A", "B", "C", "D"]
    for case in cases:
        for repeat in range(1, args.repeats + 1):
            observe(case, repeat, args.timeout)
    result = run([sys.executable, str(MERGE)], 60)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"merge failed: {result.returncode}")
    print("CORE009_OBSERVATION_COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
