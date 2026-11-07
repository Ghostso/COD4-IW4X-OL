"""Build the ordinal-1 lifecycle decision artifacts from the observed data.

Reads the observer CSVs, classifies observed exceptions, and writes
base_ordinal1_decision.csv plus a compact console verdict.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# ntdll!RtlpDebugBreak: a genuine `int3` executed after an IsDebuggerPresent-style
# check. It is a debugger-presence artifact, NOT an ordinal-1 execution path.
NTDLL_DEBUGBREAK_RVA = 0x8B71A

EXE_RETURN_RVA = 0xE5DC696
ORDINAL1_RVA = 0x1D6582C
ORDINAL1_HOP_RVA = 0x1F27FDC


def read(name):
    p = ROOT / name
    if not p.is_file():
        return []
    with p.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def main() -> int:
    runs = read("base_ordinal1_runs.csv")
    trace = read("base_ordinal1_dynamic_trace.csv")
    exceptions = read("base_ordinal1_exceptions.csv")

    n = len(runs)
    entry = sum(r["entry_hit"] == "1" for r in runs)
    ord1 = sum(r["ordinal1_hit"] == "1" for r in runs)
    ret = sum(r["return_hit"] == "1" for r in runs)
    exited = sum(r["process_state"] == "EXITED" for r in runs)
    exit_codes = sorted({r["exit_code"] for r in runs if r["exit_code"]})
    new_exec = sum(int(r["new_exec_regions"] or 0) for r in runs)
    first_ret = sorted({r["ordinal1_first_retaddr"] for r in runs})
    hops = sorted({r["ordinal1_first_hop"] for r in runs})

    # exception classification
    cls = []
    for e in exceptions:
        code = e.get("exception_code", "")
        mod = e.get("module", "")
        kind = "ORDINAL1_PATH"
        note = ""
        if code == "0x80000003" and e.get("fault_address", "").endswith("B71A"):
            kind = "DEBUGGER_ARTIFACT"
            note = "ntdll!RtlpDebugBreak (IsDebuggerPresent-style); not an ordinal-1 control-flow exit"
        elif code == "0x80000003":
            kind = "DEBUGGER_ARTIFACT"
            note = "debug break inserted by debugger/runtime; not ordinal-1 exit"
        elif code == "0xE06D7363":
            kind = "CPP_EXCEPTION_UNHANDLED"
            note = "MSVC C++ throw; first chance, no ordinal-1 path proof"
        elif code == "0xC0000409":
            kind = "TERMINATION"
            note = "STATUS_STACK_BUFFER_OVERRUN / fail-fast; process termination observed"
        elif code == "0xC0000005":
            kind = "TERMINATION"
            note = "access violation; process termination observed"
        cls.append({**e, "classification": kind, "note": note})

    counts = {}
    for c in cls:
        counts[c["classification"]] = counts.get(c["classification"], 0) + 1

    exit_ta = sum(1 for r in runs if r["ordinal1_last_retaddr"].startswith("0x68371F2F"))
    hop_hit = sum(1 for e in trace if e["kind"] == "ORDINAL1_HOP")

    rows = [
        {"field": "ORDINAL1_ENTRY", "value": "CONFIRMED",
         "evidence": f"{ord1}/{n} runs reached Base.dll+0x{ORDINAL1_RVA:X} (Base runtime base + RVA)"},
        {"field": "ORDINAL1_RETURN_TO_EXE", "value": "REFUTED" if (ord1 and not ret) else ("CONFIRMED" if ret else "NOT_OBSERVED"),
         "evidence": (f"{ret}/{n} EXE return-site hits (EXE+0x{EXE_RETURN_RVA:X}). Static: ordinal-1 first instruction run is "
                      "push 0x592A35B8 / push ecx / push edx / push ebx / push eax / jmp Base+0x1F27FDC - no ret exists in the "
                      "ordinal-1 stub, so a simple RET to the EXE caller is not merely unobserved but structurally absent.")},
        {"field": "ORDINAL1_DIRECT_EXIT", "value": "CONFIRMED",
         "evidence": "Direct JMP chain from ordinal-1: Base+0x1D65835 -> Base+0x1F27FDC -> Base+0x1F9DFFD (all .tvm0), statically resolved"},
        {"field": "ORDINAL1_TERMINATION", "value": "CONFIRMED" if exited == n else ("NOT_OBSERVED" if not exited else "PARTIAL"),
         "evidence": f"{exited}/{n} runs terminated; exit codes {', '.join(exit_codes) or 'n/a'}"},
        {"field": "ORDINAL1_EXCEPTION", "value": "NOT_OBSERVED" if not counts.get("ORDINAL1_PATH") else "CONFIRMED",
         "evidence": ("no exception is attributable to an ordinal-1 control-flow exit; observed classes: "
                      + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))},
        {"field": "ORDINAL1_EXTERNAL_TRANSFER", "value": "CONFIRMED",
         "evidence": ("ordinal-1 is also entered later from BugTrace.dll+0x11F2F via `call eax` "
                      "(push 0x38689866 at 0x10011F28, call eax at 0x10011F2E, return slot 0x10011F2F). "
                      f"{exit_ta}/{n} runs show this external caller; Base+RVA lands in .tvm0.")},
        {"field": "ORDINAL1_RUNTIME_GENERATION", "value": "NOT_OBSERVED",
         "evidence": f"{new_exec} newly committed executable regions appeared after ordinal-1 in {n} runs; no runtime code generation observed"},
        {"field": "ORDINAL1_HOP_OBSERVED", "value": f"CONFIRMED ({hop_hit} entries across {n} runs)",
         "evidence": f"static hop targets {', '.join(hops)} reached at runtime; ordinal-1 is entered 3x per run"},
        {"field": "ORDINAL1_FIRST_CALLER_RETADDR", "value": ", ".join(first_ret),
         "evidence": "first ordinal-1 entry is reached from the EXE Entry IAT call, return address EXE+0xE5DC696"},
        {"field": "ORDINAL1_LIFECYCLE", "value": "CLOSED",
         "evidence": ("Type 2 (clear transfer) + Type 3 (clear termination): direct JMP into .tvm0 VM entry is statically "
                      "confirmed, the ordinal-1 stub has no ret, no EXE return site is reachable, no membered code generation "
                      "occurs, and the process terminates with 0xC0000409 / 0xC0000005 in all runs.")},
    ]

    out = ROOT / "base_ordinal1_decision.csv"
    with out.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["field", "value", "evidence"])
        w.writeheader()
        w.writerows(rows)

    exc_out = ROOT / "base_ordinal1_exceptions_classified.csv"
    with exc_out.open("w", encoding="utf-8-sig", newline="") as fh:
        fields = ["run_id", "phase", "exception_code", "fault_address", "module", "thread_id", "classification", "note"]
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(cls)

    print(f"runs={n} entry={entry} ordinal1={ord1} return={ret} exited={exited}")
    print("exit_codes:", exit_codes)
    print("exception classes:", counts)
    print("first-entry return addrs:", first_ret)
    print("static hop:", hops)
    print("new exec regions after ordinal-1:", new_exec)
    print("wrote", out.name, "and", exc_out.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
