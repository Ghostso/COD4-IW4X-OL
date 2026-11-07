from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_rows(path: Path, rows: list[dict[str, object]], fields: list[str] | None = None) -> None:
    if fields is None:
        fields = []
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    run_files = []
    for case in "ACD":
        run_files.extend(sorted(ROOT.glob(f"exe_core009_runs_{case}_?.csv")))
    run_files.append(ROOT / "exe_core009_runs_B.csv")
    runs: list[dict[str, str]] = []
    seen: set[str] = set()
    for path in run_files:
        for row in read_rows(path):
            key = row.get("run_id", "")
            if key and key not in seen:
                seen.add(key)
                runs.append(row)
    order = {"A": 0, "B": 1, "C": 2, "D": 3}
    runs.sort(key=lambda r: (order.get(r.get("case", ""), 99), r.get("run_id", "")))
    if len(runs) != 12:
        raise SystemExit(f"expected 12 runs, got {len(runs)}")
    write_rows(ROOT / "exe_core009_runs.csv", runs)

    reg_fields = ["run_id", "case", "command_line", "entry_rva", "ordinal1_rva",
                  "eax_in", "ecx_in", "edx_in", "ebx_in", "esp_in", "ebp_in", "esi_in", "edi_in", "eflags_in",
                  "returned", "eax_out", "ecx_out", "edx_out", "eflags_out", "esp_out", "process_state", "last_observable_event"]
    write_rows(ROOT / "exe_core009_registers.csv", runs, reg_fields)

    stack_fields = ["run_id", "case", "command_line", "stack_0", "stack_4", "stack_8", "stack_C",
                    "stack_10", "stack_14", "stack_18", "returned", "process_state", "last_observable_event"]
    write_rows(ROOT / "exe_core009_stack.csv", runs, stack_fields)

    state_rows = []
    for row in runs:
        for state in ("q_gate", "src_tgp_gate", "argv_count", "argv_array", "provider_slot"):
            before = row.get(state + "_before", "")
            after = row.get(state + "_after", "")
            state_rows.append({
                "run_id": row.get("run_id", ""), "case": row.get("case", ""), "state": state,
                "before": before, "after": after,
                "delta": "UNCHANGED" if before and after and before == after else ("CHANGED" if before and after else "NO_RETURN_AFTER"),
                "repeatability": "NOT_EVALUATED_NO_RETURN",
            })
    write_rows(ROOT / "exe_core009_state_delta.csv", state_rows,
               ["run_id", "case", "state", "before", "after", "delta", "repeatability"])

    def detail_rows(kind: str) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        seen: set[tuple[str, str, str]] = set()
        paths: list[Path] = []
        for case in "ACD":
            paths.extend(sorted(ROOT.glob(f"exe_core009_{kind}_{case}_?.csv")))
        paths.append(ROOT / f"exe_core009_{kind}_B.csv")
        for path in paths:
            for row in read_rows(path):
                key = (row.get("run_id", ""), row.get("order", row.get("thread_id", "")), row.get("module_name", row.get("thread_id", "")))
                if key not in seen:
                    seen.add(key)
                    rows.append(row)
        return rows

    write_rows(ROOT / "exe_core009_module_delta.csv", detail_rows("module_delta"))
    write_rows(ROOT / "exe_core009_thread_delta.csv", detail_rows("thread_delta"))
    matrix_rows = []
    for case in "ABCD":
        group = [r for r in runs if r.get("case") == case]
        matrix_rows.append({
            "case": case,
            "runs": len(group),
            "ordinal1_hit_count": sum(r.get("ordinal1_hit") == "1" for r in group),
            "return_hit_count": sum(r.get("return_hit") == "1" for r in group),
            "process_states": ";".join(sorted({r.get("process_state", "") for r in group})),
            "exit_codes": ";".join(sorted({r.get("exit_code", "") for r in group})),
            "eax_in_unique": ";".join(sorted({r.get("eax_in", "") for r in group})),
            "ecx_in_unique": ";".join(sorted({r.get("ecx_in", "") for r in group})),
            "edx_in_unique": ";".join(sorted({r.get("edx_in", "") for r in group})),
            "ebx_in_unique": ";".join(sorted({r.get("ebx_in", "") for r in group})),
            "esp_in_unique": ";".join(sorted({r.get("esp_in", "") for r in group})),
            "ebp_in_unique": ";".join(sorted({r.get("ebp_in", "") for r in group})),
            "esi_in_unique": ";".join(sorted({r.get("esi_in", "") for r in group})),
            "edi_in_unique": ";".join(sorted({r.get("edi_in", "") for r in group})),
            "eflags_in_unique": ";".join(sorted({r.get("eflags_in", "") for r in group})),
            "stack0_unique": ";".join(sorted({r.get("stack_0", "") for r in group})),
            "stack4_unique": ";".join(sorted({r.get("stack_4", "") for r in group})),
            "module_delta": ";".join(sorted({r.get("module_delta", "") for r in group if r.get("module_delta", "")})),
        })
    write_rows(ROOT / "exe_core009_commandline_matrix.csv", matrix_rows)

    observed = [r for r in runs if r.get("ordinal1_hit") == "1"]
    returned = [r for r in runs if r.get("return_hit") == "1"]
    contract_rows = [
        {"item": "INPUT_REGISTER_CONTRACT", "classification": "UNKNOWN", "evidence": "EAX is module+RVA-stable (Base+0x1D6582C); EDX/EBX/EDI/EFLAGS stable in this environment; ECX and stack/heap pointers vary", "basis": f"{len(observed)} ordinal-1 entry observations across A-D"},
        {"item": "STACK_ARGUMENTS", "classification": "NOT_CONFIRMED", "evidence": "[ESP]/[ESP+4] contain stable runtime data in this environment; no explicit stack-argument role is proven", "basis": "stack_0..stack_18 across 12 runs"},
        {"item": "ORDINAL1_RETURNED", "classification": "NOT_CONFIRMED", "evidence": "0/12 EXE return-site breakpoint hits", "basis": "EXE RVA 0x0E5DC696"},
        {"item": "RETURN_VALUE_CONSUMER", "classification": "NOT_FOUND", "evidence": "no runtime return; CORE-008 static fall-through is zero padding and no EAX consumer", "basis": "runtime plus static caller boundary"},
        {"item": "ORDINAL1_RETURN_CONTRACT", "classification": "NOT_CONFIRMED", "evidence": "no EAX/ECX/EDX/EFLAGS/ESP return observations", "basis": "0/12 return-site hits"},
        {"item": "SIDE_EFFECT_CONTRACT", "classification": "NOT_CONFIRMED", "evidence": "no caller-side after-state exists because ordinal-1 does not return", "basis": "EXE globals before/after matrix"},
    ]
    write_rows(ROOT / "exe_core009_contract_matrix.csv", contract_rows, ["item", "classification", "evidence", "basis"])
    print(json.dumps({"runs": len(runs), "ordinal_hits": len(observed), "return_hits": len(returned)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
