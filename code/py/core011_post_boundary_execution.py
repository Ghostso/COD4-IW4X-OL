from __future__ import annotations

"""CORE-011 (E-010-01) post-boundary EXE execution test driver.

Reuses the CORE-009 observer design (x86 net48 debugger, minimal interference,
ordinal-1 entry breakpoint, fixed environment, sample hashes). Adds ONLY the
7 historical EXE candidate RVAs as image-base-relative breakpoints.
Does not modify the game EXE/DLL files.
"""

import csv
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OBSERVER_DIR = ROOT / "_core011_observer"
PROJECT = OBSERVER_DIR / "core011_post_boundary_execution.csproj"
OBSERVER = OBSERVER_DIR / "bin" / "Release" / "net48" / "core011_post_boundary_execution.exe"

# Section 10 minimal matrix: 4 runs total.
MATRIX = [
    # (environment, case, args, timeout_s)
    ("A", "noarg", [], 10),   # CORE-009 environment
    ("A", "q", ["-q"], 10),
    ("B", "noarg", [], 30),   # EX-046-like direct-launch approximation, 30s window
    ("B", "q", ["-q"], 30),
]


def run(cmd, timeout):
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=timeout,
                          encoding="utf-8", errors="replace")


def build():
    result = run(["dotnet", "build", str(PROJECT), "-c", "Release", "-v:m"], 180)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"observer build failed: {result.returncode}")
    if not OBSERVER.is_file():
        raise RuntimeError(f"observer not found: {OBSERVER}")


def execute():
    for env, case, args, timeout in MATRIX:
        cmd = [str(OBSERVER), f"--env={env}", f"--case={case}", f"--timeout={timeout}"]
        result = run(cmd, timeout + 60)
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        if result.returncode != 0:
            raise RuntimeError(f"observer env {env} case {case} failed: {result.returncode}")
        for kind in ("runs", "candidate_hits", "exceptions"):
            src = ROOT / f"exe_core011_{kind}.csv"
            dst = ROOT / f"exe_core011_{kind}_{env}_{case}.csv"
            if src.is_file():
                shutil.copyfile(src, dst)


def read_csv(path):
    # handle UTF-8 with BOM
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def merge():
    runs_rows, cand_rows, exc_rows = [], [], []
    for env, case, _args, _t in MATRIX:
        for kind, bucket in (("runs", runs_rows), ("candidate_hits", cand_rows), ("exceptions", exc_rows)):
            p = ROOT / f"exe_core011_{kind}_{env}_{case}.csv"
            if p.is_file():
                loaded = read_csv(p)
                bucket.extend(loaded)
                print(f"  loaded {len(loaded)} rows from {p.name}")
            else:
                print(f"  MISSING: {p.name}")
    print(f"TOTAL runs={len(runs_rows)} cand={len(cand_rows)} exc={len(exc_rows)}")
    for r in runs_rows:
        print(f"  {r['run_id']} ord1={r['ordinal1_hit']} state={r['process_state']}")
    # environment comparison
    fields = ["environment", "runs", "ordinal1_hits", "post_boundary_candidate_hits",
              "pre_boundary_candidate_hits", "candidate_rvas_hit", "states"]
    with open(ROOT / "exe_core011_environment_compare.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for env in ("A", "B"):
            rs = [r for r in runs_rows if r["environment"] == env]
            cs = [r for r in cand_rows if r["environment"] == env and r["breakpoint_hit"] == "1"]
            w.writerow({
                "environment": env,
                "runs": len(rs),
                "ordinal1_hits": sum(1 for r in rs if r["ordinal1_hit"] == "1"),
                "post_boundary_candidate_hits": sum(1 for c in cs if c["phase"] == "POST_BOUNDARY"),
                "pre_boundary_candidate_hits": sum(1 for c in cs if c["phase"] == "PRE_BOUNDARY"),
                "candidate_rvas_hit": ";".join(sorted({c["candidate_rva"] for c in cs})) or "NONE",
                "states": ";".join(sorted({r["process_state"] for r in rs})) or "NONE",
            })
    # decision
    ordinal1_runs = [r for r in runs_rows if r["ordinal1_hit"] == "1"]
    post = [c for c in cand_rows if c["breakpoint_hit"] == "1" and c["phase"] == "POST_BOUNDARY"]
    post_in_ordinal1_runs = [c for c in post if c["run_id"] in {r["run_id"] for r in ordinal1_runs}]
    if not ordinal1_runs:
        verdict, env_dep = "INFRASTRUCTURE_FAILURE", "UNKNOWN"
    elif post_in_ordinal1_runs:
        verdict, env_dep = "OBSERVED", "UNKNOWN"
        envs = {c["environment"] for c in post_in_ordinal1_runs}
        if len(envs) == 1:
            other = "B" if "A" in envs else "A"
            other_hits = [c for c in cand_rows if c["environment"] == other and c["breakpoint_hit"] == "1" and c["phase"] == "POST_BOUNDARY"]
            env_dep = "YES" if not other_hits else "NO"
    else:
        verdict, env_dep = "NOT_OBSERVED", "NO"
    with open(ROOT / "exe_core011_decision.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["item", "value"])
        w.writerow(["EXE_IMAGE_EXECUTION_AFTER_BOUNDARY", verdict])
        w.writerow(["ENVIRONMENT_DEPENDENT", env_dep])
        w.writerow(["runs_total", len(runs_rows)])
        w.writerow(["runs_ordinal1_hit", sum(1 for r in runs_rows if r["ordinal1_hit"] == "1")])
        w.writerow(["post_boundary_candidate_hits", len(post)])
        w.writerow(["candidates_hit", ";".join(sorted({c["candidate_rva"] for c in post})) or "NONE"])
    # merged runs
    with open(ROOT / "exe_core011_runs.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["run_id","environment","case","command_line","pid","exe_base_va","base_dll_base_va","entry_hit","ordinal1_hit","return_hit","ordinal1_timestamp_rel_process_start_s","process_state","exit_code","last_observable_event","stop_reason","notes"])
        w.writeheader()
        w.writerows(runs_rows)
    # merged candidate_hits
    with open(ROOT / "exe_core011_candidate_hits.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["run_id","environment","command_line","module","candidate_rva","runtime_va","breakpoint_hit","phase","thread_id","timestamp_relative_to_process_start_s","timestamp_relative_to_ordinal1_s","eip","eax","ecx","edx","esp","ebp","esi","edi"])
        w.writeheader()
        w.writerows(cand_rows)
    # merged exceptions
    with open(ROOT / "exe_core011_exceptions.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["run_id","environment","exception_type","eip","thread_id","timestamp_rel_process_start_s","relative_to_ordinal1_s"])
        w.writeheader()
        w.writerows(exc_rows)
    # environment compare
    fields = ["environment","runs","ordinal1_hits","post_boundary_candidate_hits","pre_boundary_candidate_hits","candidate_rvas_hit","states"]
    with open(ROOT / "exe_core011_environment_compare.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for env in ("A","B"):
            rs = [r for r in runs_rows if r["environment"] == env]
            cs = [r for r in cand_rows if r["environment"] == env and r["breakpoint_hit"] == "1"]
            w.writerow({
                "environment": env,
                "runs": len(rs),
                "ordinal1_hits": sum(1 for r in rs if r["ordinal1_hit"] == "1"),
                "post_boundary_candidate_hits": sum(1 for c in cs if c["phase"] == "POST_BOUNDARY"),
                "pre_boundary_candidate_hits": sum(1 for c in cs if c["phase"] == "PRE_BOUNDARY"),
                "candidate_rvas_hit": ";".join(sorted({c["candidate_rva"] for c in cs})) or "NONE",
                "states": ";".join(sorted({r["process_state"] for r in rs})) or "NONE",
            })
    if verdict == "NOT_OBSERVED":
        (ROOT / "STANDALONE_BOOTSTRAP_DESIGN_READY.flag").write_text("YES\n")
    print(f"DECISION EXE_IMAGE_EXECUTION_AFTER_BOUNDARY={verdict} ENVIRONMENT_DEPENDENT={env_dep}")


def main():
    build()
    execute()
    merge()
    print("CORE011_OBSERVATION_COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
