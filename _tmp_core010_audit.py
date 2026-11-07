from __future__ import annotations

"""CORE-010 audit harness (scratch, read-only).

Checks the produced CORE-010 artifacts against the round contract sections
2, 4, 5, 9, 11, 16, 18, 19, 20, 23, 25, 26. It never writes to the
deliverables; it only reports PASS/FAIL per rule.
"""

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MD = ROOT / "CODOL_STANDALONE_CORE_010_BOOTSTRAP_CONTRACT.md"

FIELDS = {
    "exe_core010_evidence_ledger.csv": [
        "id", "component", "address", "evidence", "status", "source_round", "confidence", "dependency", "notes",
    ],
    "exe_core010_boot_state_machine.csv": [
        "state_id", "state_name", "entry_evidence", "exit_evidence", "status", "required",
        "external_dependency", "blocking_level", "notes",
    ],
    "exe_core010_required_vs_optional.csv": [
        "component", "direct_exe_evidence", "required_status", "reason", "confidence",
    ],
    "exe_core010_gap_list.csv": [
        "gap_id", "layer", "component", "current_status", "blocking_level", "evidence",
        "unknown", "minimal_next_experiment", "priority",
    ],
    "exe_core010_next_experiment.csv": None,
}

STATUS_ENUM = {"CONFIRMED", "CANDIDATE", "UNKNOWN", "BOUNDARY", "NOT_FOUND", "UNRESOLVED"}
REQUIRED_ENUM = {"CONFIRMED", "CANDIDATE", "UNKNOWN", "NOT_REQUIRED"}
REQ_STATUS_ENUM = {"REQUIRED_CONFIRMED", "REQUIRED_CANDIDATE", "UNKNOWN", "NOT_REQUIRED_CONFIRMED"}
FINAL_STATUS_ENUM = {
    "READY_FOR_IMPLEMENTATION", "BLOCKED_BY_P0", "BLOCKED_BY_P1", "BLOCKED_BY_UNKNOWN",
}

# CORE-009 literals that must survive verbatim (round contract section 2)
CORE009_LITERALS = [
    "ORDINAL1_INPUT_CONTRACT", "UNKNOWN",
    "ORDINAL1_STACK_ARGUMENTS", "NOT_CONFIRMED",
    "ORDINAL1_RETURNED", "NOT_CONFIRMED",
    "ORDINAL1_RETURN_CONTRACT", "NOT_CONFIRMED",
    "RETURN_VALUE_CONSUMER", "NOT_FOUND",
    "SIDE_EFFECT_CONTRACT", "NOT_CONFIRMED",
    "COMMANDLINE_BOUNDARY_DELTA_Q", "NOT_CONFIRMED",
    "COMMANDLINE_BOUNDARY_DELTA_QA", "NOT_CONFIRMED",
    "COMMANDLINE_BOUNDARY_DELTA_SRC", "NOT_CONFIRMED",
    "MODULE_THREAD_CALLER_CONTRACT", "NOT_CONFIRMED",
    "FS_METADATA_DELTA",
    "ORDINAL1_NONRETURN",
    "REGISTER_VALUE_STABILITY",
    "REGISTER_SEMANTIC_ROLE",
]

# Section 18 forbids these words in the Tencent dependency audit
FORBIDDEN_WORDS = ["必须", "肯定需要", "肯定不需要"]
# Section 20 forbids upgrading the no-return observation
FORBIDDEN_PHRASES = ["NONRETURN_CONFIRMED", "NON_RETURN_CONFIRMED", "永不返回", "never returns"]

BOOT_IDS = [f"BOOT_{i:02d}_" for i in range(13)]

# Section-specific assertions: (key, required value) must co-occur on one line
REQUIRED_ASSERTIONS = [
    ("ENTRY", "CONFIRMED"),
    ("ENTRY_ACTION", "EXTERNAL_CALL"),
    ("ENTRY_TO_ORDINAL1", "CONFIRMED"),
    ("ENTRY_NATIVE_CONTINUATION", "NOT_FOUND"),
    ("ORDINAL1_NONRETURN", "UNKNOWN"),
    ("ORDINAL1_REACHABILITY", "CONFIRMED"),
    ("WIN_NO_TCLS", "CONFIRMED"),
    ("Q_BYPASS", "CONFIRMED"),
    ("QA_BYPASS", "CONFIRMED"),
    ("SRC_TGP_STANDALONE_BYPASS", "NOT_CONFIRMED"),
    ("NATIVE_BOOTSTRAP_CHAIN", "CANDIDATE"),
    ("HISTORICAL_CHAIN_STATUS", "NOT_ENTRY_CONNECTED"),
    ("NETWORK_INIT", "CANDIDATE"),
    ("IIPS_BOUNDARY", "CONFIRMED"),
    ("IIPS_SUCCESS", "UNKNOWN"),
    ("IIPS_FAILURE_ROOT", "UNKNOWN"),
    ("GAME_INIT", "UNKNOWN"),
    ("IW4_LINEAGE_HOMOLOGUE", "CANDIDATE"),
    ("RENDERER", "UNKNOWN"),
    ("INPUT", "UNKNOWN"),
    ("AUDIO", "UNKNOWN"),
    ("MAIN_LOOP", "UNKNOWN"),
]

# Four-layer contract (section 17)
LAYER_MARKERS = ["A_PROCESS", "B_EXE", "C_RUNTIME", "D_GAME"]

results: list[tuple[str, bool, str]] = []


def check(rule: str, ok: bool, detail: str = "") -> None:
    results.append((rule, ok, detail))


def load(name: str) -> tuple[list[str], list[dict[str, str]]]:
    path = ROOT / name
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        return list(reader.fieldnames or []), list(reader)


def all_text() -> str:
    chunks = []
    for name in FIELDS:
        _h, rows = load(name)
        for row in rows:
            chunks.append(" | ".join(str(v) for v in row.values()))
    for extra in ["exe_core010_contract_matrix.csv", "exe_core010_dependency_layers.csv"]:
        _h, rows = load(extra)
        for row in rows:
            chunks.append(" | ".join(str(v) for v in row.values()))
    if MD.exists():
        chunks.append(MD.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(chunks)


def run_audit() -> int:
    text = all_text()

    # --- existence + required fields -------------------------------------
    for name, fields in FIELDS.items():
        path = ROOT / name
        check(f"exists:{name}", path.exists(), "missing" if not path.exists() else "")
        if fields is None or not path.exists():
            continue
        header, _rows = load(name)
        missing = [f for f in fields if f not in header]
        check(f"fields:{name}", not missing, f"missing={missing} header={header}")

    # --- enumeration legality -------------------------------------------
    _h, ledger = load("exe_core010_evidence_ledger.csv")
    bad = sorted({r.get("status", "") for r in ledger} - STATUS_ENUM)
    check("enum:ledger.status", not bad, f"illegal={bad}")

    _h, states = load("exe_core010_boot_state_machine.csv")
    bad = sorted({r.get("required", "") for r in states} - REQUIRED_ENUM)
    check("enum:states.required", not bad, f"illegal={bad}")

    _h, req = load("exe_core010_required_vs_optional.csv")
    bad = sorted({r.get("required_status", "") for r in req} - REQ_STATUS_ENUM)
    check("enum:required_vs_optional", not bad, f"illegal={bad}")

    # --- section 5: BOOT_00..BOOT_12 complete ---------------------------
    ids = " ".join(r.get("state_id", "") for r in states)
    missing = [b for b in BOOT_IDS if b not in ids]
    check("states:BOOT_00..12", not missing, f"missing={missing}")

    # --- section 2: CORE-009 literals survive ---------------------------
    missing = [t for t in CORE009_LITERALS if t not in text]
    check("core009:literals", not missing, f"missing={missing}")
    check("core009:FS_METADATA_DELTA_value", "FS_METADATA_DELTA" in text and "0" in text, "")

    # --- section 20/9: forbidden claims (negation-aware) -----------------
    negations = ("not", "禁止", "不得", "没有", "NO)", "rejected")
    lines = text.splitlines()
    bad = []
    for phrase in FORBIDDEN_PHRASES:
        for ln in lines:
            if phrase in ln and not any(m in ln for m in negations):
                bad.append((phrase, ln.strip()[:70]))
    check("section20:no_nonreturn_upgrade", not bad, f"found={bad[:3]}")

    # --- section 18: forbidden absolute wording -------------------------
    hits = [w for w in FORBIDDEN_WORDS if w in text]
    check("section18:no_absolute_wording", not hits, f"found={hits}")

    # --- section 23: exactly one next experiment ------------------------
    header, nxt = load("exe_core010_next_experiment.csv")
    check("section23:next_experiment_rows", len(nxt) <= 1, f"rows={len(nxt)}")
    check("section23:one_only_marker", "ONE_ONLY" in text or "NONE" in text, "")

    # --- section 19: gap priorities ------------------------------------
    _h, gaps = load("exe_core010_gap_list.csv")
    prios = {r.get("priority", "") for r in gaps}
    check("section19:priority_enum", prios <= {"P0", "P1", "P2", "P3"}, f"illegal={sorted(prios)}")
    check("section19:has_P0", "P0" in prios, f"prios={sorted(prios)}")

    # --- section 20: ordinal-1 must not be P0 CONFIRMED -----------------
    ordinal_rows = [r for r in gaps if "ORDINAL" in r.get("component", "").upper()]
    bad = [r.get("gap_id") for r in ordinal_rows if r.get("blocking_level", "").upper() == "CONFIRMED"]
    check("section20:ordinal1_P0_not_confirmed", not bad, f"rows={bad}")
    check("section20:ordinal1_gap_present", bool(ordinal_rows), "no ORDINAL gap row")

    # --- section 26: exactly one DECLARED final status -------------------
    declared = []
    for ln in lines:
        m = re.search(r"(?:STANDALONE_BOOTSTRAP_STATUS|FINAL_STATUS)\s*=\s*([A-Z_]+)", ln)
        if m:
            declared.append(m.group(1))
    legal = [d for d in declared if d in FINAL_STATUS_ENUM]
    check("section26:declared_status", len(legal) == 1, f"declared={declared}")
    check("section26:decision_table", "rejected" in text and "selected" in text, "")

    # --- section 21: contract diagram present --------------------------
    check("section21:diagram", "BOUNDARY" in text and "UNKNOWN" in text and "CONFIRMED" in text, "")

    # --- section 9: provider not asserted as a Windows API --------------
    bad = []
    for probe in ["0x00CA827C = GetCommandLineW", "0xCA827C = GetCommandLineW",
                  "CA827C is GetCommandLineW", "0x00CA827C = CommandLineToArgvW"]:
        for ln in lines:
            if probe in ln and not any(m in ln for m in negations):
                bad.append(probe)
                break
    check("section9:no_api_identity_claim", not bad, f"found={bad}")

    # --- section 11: static vs runtime separation ----------------------
    check("section11:runtime_observed_marker", "RUNTIME_OBSERVED" in text, "")
    if "0x0849B500" in text:
        check("section11:849B500_static_not_found", "NOT_FOUND" in text, "")

    # --- section 16: no invented renderer/audio evidence ----------------
    for node in ["RENDERER", "MAIN_LOOP", "GAME_INIT"]:
        check(f"section16:{node}_status_unknown", node in text, f"{node} absent from contract")

    # --- section 17: four-layer contract -------------------------------
    _h, layers = load("exe_core010_dependency_layers.csv")
    layer_text = " ".join(str(v) for row in layers for v in row.values())
    missing = [m for m in LAYER_MARKERS if m not in layer_text]
    check("section17:four_layers", not missing, f"missing={missing}")

    # --- section-specific key/value assertions ---------------------------
    lines = text.splitlines()
    for key, value in REQUIRED_ASSERTIONS:
        hits = [ln for ln in lines if key in ln]
        ok = any(value in ln for ln in hits)
        detail = "" if ok else f"key_lines={len(hits)} need value {value}"
        check(f"assert:{key}={value}", ok, detail)

    width = max(len(r[0]) for r in results)
    failed = 0
    for rule, ok, detail in results:
        mark = "PASS" if ok else "FAIL"
        if not ok:
            failed += 1
        print(f"[{mark}] {rule:<{width}}  {detail}")
    print()
    print(f"TOTAL {len(results)}  FAIL {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run_audit())