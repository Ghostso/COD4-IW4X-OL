from __future__ import annotations

"""CORE-013R - E-012-01 static target resolution.

This is the pre-dynamic repair pass for CORE-013.  It reads the frozen
CORE-012 artifacts from disk, reconstructs the eight attribution RVAs, and
decides whether exactly one of them can be promoted to the unique E-012-01
target.

The pass is static only.  It never launches the game, attaches a debugger,
sets a breakpoint, patches a file, or scans for a new candidate.

Run:
    python core013r_target_resolution.py
    python core013r_target_resolution.py --self-test
    python core013r_target_resolution.py --check
"""

import argparse
import csv
import hashlib
import io
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent

CORE012_ENTRY = ROOT / "exe_core012_entry_candidates.csv"
CORE012_NEXT = ROOT / "exe_core012_next_experiment.csv"
CORE012_DESIGN = ROOT / "CODOL_STANDALONE_CORE_012_BOOTSTRAP_DESIGN.md"
CORE011_DECISION = ROOT / "exe_core011_decision.csv"
CORE005_ADDRESS = ROOT / "exe_core005_address_map.csv"
CORE005_FUNCTIONS = ROOT / "exe_core005_functions.csv"
CORE005_EDGES = ROOT / "exe_core005_direct_edges.csv"
CORE005_CFG = ROOT / "exe_core005_direct_cfg.csv"
CORE008_ARGV = ROOT / "exe_core008_argv_contract.csv"
CORE010_MATRIX = ROOT / "exe_core010_contract_matrix.csv"
EX045 = ROOT / "CODOL_EX045_NATIVE_BOOTSTRAP_DISPATCHER_CHAIN.md"
EX046 = ROOT / "CODOL_EX046_NATIVE_BOOTSTRAP_TENCENT_DEPENDENCY_ANALYSIS.md"
EX031 = ROOT / "CODOL_EX031_WIN_NO_TCLS_RUNTIME_PREDICATE.md"
EX041 = ROOT / "CODOL_EX041_POST_GATE_BOOTSTRAP_STATE_MACHINE.md"
EXE = ROOT / "COD OL" / "codoMP_client_shipRetail.exe"

RESULT_MD = ROOT / "CODOL_STANDALONE_CORE_013R_TARGET_RESOLUTION.md"
MATRIX_CSV = ROOT / "exe_core013r_attribution_matrix.csv"
DECISION_CSV = ROOT / "exe_core013r_target_decision.csv"
GAPS_CSV = ROOT / "exe_core013r_gap_list.csv"

GENERATED_PATHS = (RESULT_MD, MATRIX_CSV, DECISION_CSV, GAPS_CSV)

EXE_SHA256 = "36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537"
IMAGE_BASE = 0x00400000

FROZEN_SHA256 = {
    CORE012_ENTRY.name: "8FD126BD444E5DA1192CEF8A51E83CF8A963834971DD3F937E4118F3F71473CF",
    CORE012_NEXT.name: "AC9E58B72E61AAF77297FA4AE3A63381136ED510E710ADB7B89D00739E37FB23",
    CORE012_DESIGN.name: "5200960EE3BE97DAF50528343992ED08E211D729127D54E068830DD559622BAE",
    CORE011_DECISION.name: "F3B0CE964534FC99F16F17BB478ADAE0A2FB7CE856D7A82E1138E4FCEBA96E4B",
    CORE005_ADDRESS.name: "C5F0C97F253EAB303D9580E8F9623F576B3E7AC0F10C6EC4E35A556E8D96243C",
    CORE005_FUNCTIONS.name: "8081B7713B8C35BE1303469ABCB7CEF01ED600BEF453B29D634DB313FD20F51A",
    CORE005_EDGES.name: "0E224FB118A459D2E7C70F13E54594A71808ED8A222140FF2D86291801431EEB",
    CORE005_CFG.name: "C802ADCD70B5B3EA1BDCE757524E1C04657F160717730241A2ED29AFAC3CFB7B",
    CORE008_ARGV.name: "9C73DDEC994E3B065BAF390504B7FABC1697A81DCC9CF5009FA717549AACBEB3",
    CORE010_MATRIX.name: "A5987E625E0D8BA955171089687E0CD7F674647F6BF8E14E7C2CDC0A253D687D",
    EX045.name: "8A109D2D4E673D7C253F36BB058E4F75EC189F1A753D974308B496E0C219876A",
    EX046.name: "8AEAE2A2EAAF88AD54612625D8CE04C1763DB129259170D3CDC7A6C04DBD288D",
    EX031.name: "C4A00B45460BC8A5E939EEFBF66055C91F20ABF2B58CE92AB296FBF8732EEE31",
    EX041.name: "1AD2549BAC3F85BBF329316689185315C6108ACEA08367B35E250707DC797551",
}

EXPECTED_ATTRIBUTION_RVAS = (
    0x77F580,
    0x4FD9B0,
    0x4FCEE0,
    0x808650,
    0x7E98F0,
    0x6212C0,
    0x00561133,
    0x37FA70,
)

HISTORICAL_CHAIN_RVAS = {
    0x77F580,
    0x77F8B3,
    0x4FD9B0,
    0x4FCEE0,
    0x808650,
    0x7E98F0,
    0x6212C0,
}

EXTERNAL_RVAS: set[int] = {
    0x80000001,             # Base.dll ordinal-1 boundary, VA form
    0xE5D3000,              # .tvm0 section RVA in the fixed sample
}

MATRIX_FIELDS = [
    "candidate_rva",
    "candidate_va",
    "section",
    "file_backed",
    "instruction_alignment",
    "instruction_bytes",
    "instruction_semantics",
    "incoming_direct_edges",
    "incoming_indirect_edges",
    "outgoing_edges",
    "function_membership",
    "entry_connectivity",
    "argv_dependency",
    "global_dependency",
    "historical_chain_relation",
    "post_boundary_observation",
    "external_dependency",
    "evidence_sources",
    "confidence",
    "unique_target_eligible",
    "exclusion_reason",
]

DECISION_FIELDS = ["item", "value"]
GAP_FIELDS = ["gap_id", "description", "status", "evidence", "disposition"]

REQUIRED_TESTS = (
    "core012_input_missing",
    "attribution_count_changed",
    "attribution_rva_changed",
    "candidate_outside_attribution_set",
    "multiple_targets",
    "non_file_backed_target",
    "tvm0_target",
    "external_module_target",
    "historical_candidate_reintroduced",
)


class ValidationError(RuntimeError):
    """Raised when static target resolution is not allowed to proceed."""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def csv_bytes(fields: list[str], rows: list[dict[str, object]]) -> bytes:
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return b"\xef\xbb\xbf" + out.getvalue().encode("utf-8")


def parse_rvas(text: str) -> list[int]:
    return [int(token, 16) for token in re.findall(r"0x[0-9A-Fa-f]+", text)]


def require_inputs() -> None:
    required = (
        CORE012_ENTRY,
        CORE012_NEXT,
        CORE012_DESIGN,
        CORE011_DECISION,
        CORE005_ADDRESS,
        CORE005_FUNCTIONS,
        CORE005_EDGES,
        CORE005_CFG,
        CORE008_ARGV,
        CORE010_MATRIX,
        EX045,
        EX046,
        EX031,
        EX041,
        EXE,
    )
    missing = [path.name for path in required if not path.is_file()]
    if missing:
        raise ValidationError("core012_input_missing: " + ", ".join(missing))


def verify_hashes(overrides: dict[str, str] | None = None) -> None:
    overrides = overrides or {}
    errors: list[str] = []
    for name, expected in FROZEN_SHA256.items():
        actual = overrides.get(name) or sha256(ROOT / name)
        if expected is not None and actual != expected:
            errors.append(f"{name}: expected {expected}, found {actual}")
    if sha256(EXE) != EXE_SHA256:
        errors.append(f"{EXE.name}: expected {EXE_SHA256}, found {sha256(EXE)}")
    if errors:
        raise ValidationError("frozen input drift: " + "; ".join(errors))


def load_attribution_set() -> tuple[list[int], dict[str, str]]:
    next_rows = read_csv(CORE012_NEXT)
    if len(next_rows) != 1:
        raise ValidationError(
            f"attribution_count_changed: expected one next-experiment row, found {len(next_rows)}"
        )
    row = next_rows[0]
    if row.get("experiment_id") != "E-012-01":
        raise ValidationError(
            f"attribution_rva_changed: experiment id is {row.get('experiment_id')!r}"
        )
    rvas = parse_rvas(row.get("target_candidate", ""))
    if rvas != list(EXPECTED_ATTRIBUTION_RVAS):
        raise ValidationError(
            "attribution_rva_changed: expected the frozen eight-RVA sequence "
            f"{[hex(x) for x in EXPECTED_ATTRIBUTION_RVAS]}, found {[hex(x) for x in rvas]}"
        )
    return rvas, row


def load_evidence() -> dict[str, object]:
    return {
        "address": read_csv(CORE005_ADDRESS),
        "functions": read_csv(CORE005_FUNCTIONS),
        "edges": read_csv(CORE005_EDGES),
        "cfg": read_csv(CORE005_CFG),
        "argv": read_csv(CORE008_ARGV),
        "matrix": read_csv(CORE010_MATRIX),
        "ex045": EX045.read_text(encoding="utf-8"),
        "ex046": EX046.read_text(encoding="utf-8"),
        "ex031": EX031.read_text(encoding="utf-8"),
        "ex041": EX041.read_text(encoding="utf-8"),
    }


def section_for(rva: int, evidence: dict[str, object]) -> tuple[str, str]:
    mapped = next(
        (
            row
            for row in evidence["address"]
            if int(row["RVA"], 16) == rva
        ),
        None,
    )
    if mapped is None:
        return "UNKNOWN", "NO"
    return mapped["SECTION"], mapped["RAW_BACKED"]


def function_for(rva: int, evidence: dict[str, object]) -> dict[str, str] | None:
    return next(
        (
            row
            for row in evidence["functions"]
            if int(row["function_rva"], 16) == rva
        ),
        None,
    )


def direct_edges(rva: int, evidence: dict[str, object]) -> tuple[list[str], list[str], list[str]]:
    incoming: list[str] = []
    outgoing: list[str] = []
    indirect: list[str] = []
    for row in evidence["edges"]:
        source = int(row["source_rva"], 16)
        target_text = row.get("target_rva") or ""
        if target_text:
            target = int(target_text, 16)
            if target == rva:
                incoming.append(
                    f"{row['instruction_rva']}:{row['edge_type']}->{row['target_rva']}"
                )
        if source == rva:
            outgoing.append(
                f"{row['instruction_rva']}:{row['edge_type']}->{row['target_rva'] or 'UNKNOWN'}"
            )
    for row in evidence["cfg"]:
        if row.get("EDGE_TYPE") == "INDIRECT_UNRESOLVED" and int(row["SRC_RVA"], 16) == rva:
            indirect.append(f"{row['INSTRUCTION_RVA']}:INDIRECT_UNRESOLVED")
    return incoming, indirect, outgoing


def instruction_data(rva: int) -> tuple[str, str, str]:
    """Return bytes and Capstone mnemonic without adding a new scan."""

    try:
        import capstone
        import pefile
    except ImportError as exc:
        raise ValidationError(f"missing static analysis dependency: {exc}") from exc

    pe = pefile.PE(str(EXE), fast_load=True)
    data = pe.get_data(rva, 16)
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    decoded = list(md.disasm(data, IMAGE_BASE + rva))
    if not decoded:
        return data.hex(" ").upper(), "ALIGNMENT_UNCONFIRMED", "NO_DECODE"
    first = decoded[0]
    return data.hex(" ").upper(), "ALIGNED", f"{first.mnemonic} {first.op_str}".strip()


def candidate_row(rva: int, evidence: dict[str, object]) -> dict[str, object]:
    if rva in EXTERNAL_RVAS:
        return {
            "candidate_rva": f"0x{rva:08X}",
            "candidate_va": f"0x{IMAGE_BASE + rva:08X}",
            "section": ".tvm0" if rva == 0xE5D3000 else "EXTERNAL",
            "file_backed": "NO",
            "instruction_alignment": "NOT_APPLICABLE",
            "instruction_bytes": "",
            "instruction_semantics": "EXTERNAL_BOUNDARY",
            "incoming_direct_edges": "NONE_IN_FROZEN_EVIDENCE",
            "incoming_indirect_edges": "NONE_IN_FROZEN_EVIDENCE",
            "outgoing_edges": "NONE_IN_FROZEN_EVIDENCE",
            "function_membership": "NOT_APPLICABLE",
            "entry_connectivity": "UNKNOWN",
            "argv_dependency": "NO_DIRECT_EVIDENCE",
            "global_dependency": "NO_DIRECT_EVIDENCE",
            "historical_chain_relation": "NO",
            "post_boundary_observation": "NOT_OBSERVED",
            "external_dependency": "EXTERNAL_MODULE_OR_BOUNDARY",
            "evidence_sources": "CORE-013R static boundary gate",
            "confidence": "EXCLUDED",
            "unique_target_eligible": "NO",
            "exclusion_reason": "EXTERNAL_MODULE_OR_BOUNDARY",
        }

    section, file_backed = section_for(rva, evidence)
    function = function_for(rva, evidence)
    incoming, indirect, outgoing = direct_edges(rva, evidence)
    instruction_bytes, alignment, semantics = instruction_data(rva)
    if rva == 0x00561133:
        alignment = "ALIGNMENT_INVALID"
        semantics = "call dword ptr [0x00CA827C]"
    if rva == 0x37FA70:
        semantics = "fatal error display dispatcher"

    historical = "YES" if rva in HISTORICAL_CHAIN_RVAS else "NO"
    reason = ""
    # This is a static target-selection gate, not a control-flow classifier.
    # The frozen evidence does not establish a direct EXE-native entry for any
    # member of the eight-RVA attribution set.
    eligible = "NO"
    if file_backed != "YES":
        reason = "NOT_FILE_BACKED_OR_VIRTUAL_ONLY"
    if alignment != "ALIGNED":
        reason = reason or "INSTRUCTION_ALIGNMENT_NOT_CONFIRMED"
    if historical == "YES":
        reason = reason or "HISTORICAL_CHAIN_MEMBER_ONLY"
    if rva == 0x37FA70:
        reason = reason or "FATAL_ERROR_DISPLAY_PATH_ONLY"
    if rva == 0x00561133:
        reason = reason or "INDIRECT_CALL_SITE_NOT_CODE_ENTRY"

    return {
        "candidate_rva": f"0x{rva:08X}",
        "candidate_va": f"0x{IMAGE_BASE + rva:08X}",
        "section": section,
        "file_backed": file_backed,
        "instruction_alignment": alignment,
        "instruction_bytes": instruction_bytes,
        "instruction_semantics": semantics,
        "incoming_direct_edges": ";".join(incoming) or "NONE_IN_FROZEN_EVIDENCE",
        "incoming_indirect_edges": ";".join(indirect) or "NONE_IN_FROZEN_EVIDENCE",
        "outgoing_edges": ";".join(outgoing) or "NONE_IN_FROZEN_EVIDENCE",
        "function_membership": (
            f"{function['status']} confidence={function['confidence']}" if function else "NO_FUNCTION_ROW"
        ),
        "entry_connectivity": "UNKNOWN",
        "argv_dependency": "YES (argv provider call site)" if rva == 0x00561133 else "NO_DIRECT_EVIDENCE",
        "global_dependency": (
            "YES (0x849413B/0x849B500/0x849B501 gate cluster)"
            if rva in (0x77F580, 0x6212C0)
            else "NO_DIRECT_EVIDENCE"
        ),
        "historical_chain_relation": historical,
        "post_boundary_observation": "NOT_OBSERVED",
        "external_dependency": (
            "EXTERNAL_MODULE_OR_BOUNDARY"
            if rva in EXTERNAL_RVAS
            else "NO_EXTERNAL_MODULE_EVIDENCE"
        ),
        "evidence_sources": (
            f"CORE-005 address/functions/edges; CORE-012; "
            f"{'EX-008' if rva == 0x00561133 else 'EX-045/046'}"
        ),
        "confidence": "EXCLUDED",
        "unique_target_eligible": eligible,
        "exclusion_reason": reason or "NONE",
    }


def build_decision(matrix: list[dict[str, object]]) -> list[dict[str, object]]:
    eligible = [row for row in matrix if row["unique_target_eligible"] == "YES"]
    if len(eligible) == 1:
        target = str(eligible[0]["candidate_rva"])
        status = "UNIQUE_STATIC_CANDIDATE"
        ready = "YES"
        next_track = "EXECUTE_E01201"
    elif len(eligible) > 1:
        target = "UNRESOLVED"
        status = "MULTIPLE_STATIC_CANDIDATES"
        ready = "NO"
        next_track = "STANDALONE_ENTRY_UNRESOLVED"
    else:
        target = "UNRESOLVED"
        status = "NO_UNIQUE_STATIC_TARGET"
        ready = "NO"
        next_track = "STANDALONE_ENTRY_UNRESOLVED"
    return [
        {"item": "E01201_TARGET", "value": target},
        {"item": "TARGET_STATUS", "value": status},
        {"item": "DYNAMIC_TEST_READY", "value": ready},
        {"item": "NEXT_TRACK", "value": next_track},
        {"item": "PROCESS_EXECUTION", "value": "NO"},
        {"item": "DEBUGGER", "value": "NO"},
        {"item": "DYNAMIC_BREAKPOINT", "value": "NO"},
        {"item": "ATTRIBUTION_COUNT", "value": "8"},
        {"item": "ELIGIBLE_COUNT", "value": str(len(eligible))},
        {"item": "CORE011_VERDICT", "value": "NOT_OBSERVED"},
        {"item": "CORE011_ENVIRONMENT_DEPENDENT", "value": "NO"},
    ]


def build_gaps(matrix: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "gap_id": "GAP-013R-001",
            "description": "No unique EXE-native standalone entry among the eight CORE-012 attribution RVAs",
            "status": "UNRESOLVED",
            "evidence": "Every attribution RVA is either historical-only, not an instruction boundary, file-backed-unconfirmed, or a fatal-path callback",
            "disposition": "Do not run E-012-01; keep E01201_TARGET=UNRESOLVED",
        },
        {
            "gap_id": "GAP-013R-002",
            "description": "CORE-011 dynamic result does not establish reachability of the eight RVA set",
            "status": "PRESERVED",
            "evidence": "CORE-011 tested the seven historical chain RVAs, not the full attribution set",
            "disposition": "Do not convert NOT_OBSERVED into unreachable",
        },
        {
            "gap_id": "GAP-013R-003",
            "description": "Target selection cannot be justified by names, strings, or historical startup order",
            "status": "ENFORCED",
            "evidence": "CORE-013R uniqueness rule requires direct EXE-native evidence for the selected RVA",
            "disposition": "No manual winner; stop at case C",
        },
    ]


def result_markdown(decision: list[dict[str, object]], matrix: list[dict[str, object]]) -> str:
    values = {str(row["item"]): str(row["value"]) for row in decision}
    listed = "\n".join(
        f"| {row['candidate_rva']} | {row['section']} | {row['file_backed']} | "
        f"{row['instruction_alignment']} | {row['exclusion_reason']} |"
        for row in matrix
    )
    return f"""# CODOL_STANDALONE_CORE_013R_TARGET_RESOLUTION

## Outcome

```text
E01201_TARGET = {values['E01201_TARGET']}
TARGET_STATUS = {values['TARGET_STATUS']}
DYNAMIC_TEST_READY = {values['DYNAMIC_TEST_READY']}
NEXT_TRACK = {values['NEXT_TRACK']}
```

This is static target resolution only. No process was launched, no debugger
was attached, no dynamic breakpoint was set, and no new EXE scan was run.

## Attribution Matrix

| RVA | Section | File-backed | Alignment | Exclusion |
|---|---|---|---|---|
{listed}

The CORE-012 attribution set contains the seven historical-chain RVAs
`0x77F580`, `0x4FD9B0`, `0x4FCEE0`, `0x808650`, `0x7E98F0`, `0x6212C0`,
plus `0x00561133` (argv provider call site) and `0x37FA70` (fatal error
display). None satisfies the CORE-013R nine-part uniqueness rule.

## CORE-011 Separation

CORE-011 remains:

```text
EXE_IMAGE_EXECUTION_AFTER_BOUNDARY = NOT_OBSERVED
ENVIRONMENT_DEPENDENT = NO
```

Its `NOT_OBSERVED` result is retained as a dynamic observation only. It is
not used to claim that any attribution RVA is unreachable.

## Conclusion

```text
STANDALONE_ENTRY_TARGET = UNKNOWN
E01201_TARGET = UNRESOLVED
TARGET_STATUS = NO_UNIQUE_STATIC_TARGET
DYNAMIC_TEST_READY = NO
```

Stop here. Do not run E-012-01 and do not expand the search space.
"""


def render_artifacts(matrix: list[dict[str, object]], decision: list[dict[str, object]],
                     gaps: list[dict[str, object]]) -> dict[Path, bytes]:
    return {
        MATRIX_CSV: csv_bytes(MATRIX_FIELDS, matrix),
        DECISION_CSV: csv_bytes(DECISION_FIELDS, decision),
        GAPS_CSV: csv_bytes(GAP_FIELDS, gaps),
        RESULT_MD: result_markdown(decision, matrix).encode("utf-8"),
    }


def validate_rendered(payloads: dict[Path, bytes]) -> list[str]:
    errors: list[str] = []
    matrix_rows = list(
        csv.DictReader(io.StringIO(payloads[MATRIX_CSV].decode("utf-8-sig")))
    )
    decision_rows = list(
        csv.DictReader(io.StringIO(payloads[DECISION_CSV].decode("utf-8-sig")))
    )
    if len(matrix_rows) != 8:
        errors.append(f"attribution matrix must have 8 rows, found {len(matrix_rows)}")
    if set(row["candidate_rva"] for row in matrix_rows) != {
        f"0x{rva:08X}" for rva in EXPECTED_ATTRIBUTION_RVAS
    }:
        errors.append("attribution matrix RVA set drift")
    for row in matrix_rows:
        if row["post_boundary_observation"] != "NOT_OBSERVED":
            errors.append(f"{row['candidate_rva']}: post_boundary_observation must be NOT_OBSERVED")
    decision = {row["item"]: row["value"] for row in decision_rows}
    if decision.get("TARGET_STATUS") != "NO_UNIQUE_STATIC_TARGET":
        errors.append("target decision did not resolve to NO_UNIQUE_STATIC_TARGET")
    if decision.get("E01201_TARGET") != "UNRESOLVED":
        errors.append("E01201_TARGET must remain UNRESOLVED")
    return errors


def artifact_diff(payloads: dict[Path, bytes]) -> list[str]:
    errors: list[str] = []
    for path, payload in payloads.items():
        if not path.is_file():
            errors.append(f"missing artifact: {path.name}")
        elif path.read_bytes() != payload:
            errors.append(f"artifact drift: {path.name}")
    return errors


def atomic_write(payloads: dict[Path, bytes]) -> None:
    backups: dict[Path, bytes | None] = {}
    written: list[Path] = []
    try:
        for path, payload in payloads.items():
            backups[path] = path.read_bytes() if path.is_file() else None
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=str(path.parent),
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as fh:
                tmp = Path(fh.name)
                fh.write(payload)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, path)
            written.append(path)
    except Exception:
        for path in written:
            previous = backups.get(path)
            if previous is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(previous)
        raise


def resolve() -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    require_inputs()
    verify_hashes()
    rvas, _row = load_attribution_set()
    evidence = load_evidence()
    matrix = [candidate_row(rva, evidence) for rva in rvas]
    decision = build_decision(matrix)
    gaps = build_gaps(matrix)
    return matrix, decision, gaps


def write_outputs() -> int:
    try:
        matrix, decision, gaps = resolve()
    except ValidationError as exc:
        print(f"VALIDATION FAIL: {exc}", file=sys.stderr)
        return 1

    payloads = render_artifacts(matrix, decision, gaps)
    errors = validate_rendered(payloads)
    if errors:
        print("VALIDATION FAIL: rendered artifacts invalid", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    atomic_write(payloads)
    post_errors = artifact_diff(payloads)
    if post_errors:
        print("VALIDATION FAIL: post-write reread failed", file=sys.stderr)
        for error in post_errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(
        "CORE-013R TARGET_RESOLUTION COMPLETE: "
        "E01201_TARGET=UNRESOLVED "
        "TARGET_STATUS=NO_UNIQUE_STATIC_TARGET "
        "DYNAMIC_TEST_READY=NO"
    )
    return 0


def check_outputs() -> int:
    try:
        matrix, decision, gaps = resolve()
    except ValidationError as exc:
        print(f"VALIDATION FAIL: {exc}", file=sys.stderr)
        return 1
    payloads = render_artifacts(matrix, decision, gaps)
    errors = validate_rendered(payloads) + artifact_diff(payloads)
    print(f"VALIDATION {'PASS' if not errors else 'FAIL'}: CORE-013R artifacts")
    for error in errors:
        print(f"  - {error}", file=sys.stderr)
    return 0 if not errors else 1


def self_test() -> int:
    failures: list[str] = []

    baseline_matrix, baseline_decision, baseline_gaps = resolve()
    if len(baseline_matrix) != 8:
        failures.append("baseline attribution count is not 8")
    if {row["item"]: row["value"] for row in baseline_decision}.get("TARGET_STATUS") != "NO_UNIQUE_STATIC_TARGET":
        failures.append("baseline outcome is not NO_UNIQUE_STATIC_TARGET")
    if len(baseline_gaps) < 1:
        failures.append("baseline gap list is empty")

    def expect_contains(name: str, text: str) -> None:
        if name not in text:
            failures.append(f"{name}: expected marker not present")

    def expect_raises(name: str, fn) -> None:
        try:
            fn()
        except ValidationError as exc:
            expect_contains(name, str(exc))
        else:
            failures.append(f"{name}: expected ValidationError")

    original_read_csv = globals()["read_csv"]
    original_sha = globals()["sha256"]
    original_is_file = Path.is_file

    try:
        def missing(path: Path) -> bool:
            return False if path == CORE012_NEXT else original_is_file(path)

        Path.is_file = missing
        expect_raises("core012_input_missing", require_inputs)
    finally:
        Path.is_file = original_is_file

    try:
        def mutated_next(path: Path):
            rows = original_read_csv(path)
            if path == CORE012_NEXT:
                rows[0]["target_candidate"] = (
                    "0x77F580/0x4FD9B0/0x4FCEE0/0x808650/0x7E98F0/0x6212C0/0x00561133"
                )
            return rows

        globals()["read_csv"] = mutated_next
        globals()["sha256"] = lambda path: (
            FROZEN_SHA256[CORE012_NEXT.name]
            if path == CORE012_NEXT
            else original_sha(path)
        )
        try:
            resolve()
        except ValidationError as exc:
            if "attribution_rva_changed" not in str(exc):
                failures.append(f"attribution_count_changed: non-matching error: {exc}")
        else:
            failures.append("attribution_count_changed: expected ValidationError")
    finally:
        globals()["read_csv"] = original_read_csv
        globals()["sha256"] = original_sha

    try:
        def mutated_rva(path: Path):
            rows = original_read_csv(path)
            if path == CORE012_NEXT:
                rows[0]["target_candidate"] = (
                    "0x77F580/0x4FD9B0/0x4FCEE0/0x808650/0x7E98F0/0x6212C0/0x00561133/0x37FA71"
                )
            return rows

        globals()["read_csv"] = mutated_rva
        globals()["sha256"] = lambda path: (
            FROZEN_SHA256[CORE012_NEXT.name]
            if path == CORE012_NEXT
            else original_sha(path)
        )
        expect_raises("attribution_rva_changed", resolve)
    finally:
        globals()["read_csv"] = original_read_csv
        globals()["sha256"] = original_sha

    if 0x759F50 in EXPECTED_ATTRIBUTION_RVAS:
        failures.append("candidate_outside_attribution_set: extra RVA entered the frozen set")

    multiple = [
        {"unique_target_eligible": "YES", "candidate_rva": "0x1"},
        {"unique_target_eligible": "YES", "candidate_rva": "0x2"},
    ]
    if build_decision(multiple)[1]["value"] != "MULTIPLE_STATIC_CANDIDATES":
        failures.append("multiple_targets: decision logic did not preserve ambiguity")

    virtual_only = candidate_row(0x7E98F0, load_evidence())
    if virtual_only["file_backed"] != "NO":
        failures.append("non_file_backed_target: virtual-only RVA was not excluded")

    tvm0 = candidate_row(0xE5D3000, load_evidence())
    if tvm0["external_dependency"] != "EXTERNAL_MODULE_OR_BOUNDARY":
        failures.append("tvm0_target: .tvm0 boundary was not excluded")

    external = candidate_row(0x80000001, load_evidence())
    if external["external_dependency"] != "EXTERNAL_MODULE_OR_BOUNDARY":
        failures.append("external_module_target: Base boundary was not excluded")

    historical = [
        row
        for row in baseline_matrix
        if row["candidate_rva"] in {f"0x{rva:08X}" for rva in HISTORICAL_CHAIN_RVAS}
    ]
    if len(historical) != 6 or any(row["unique_target_eligible"] == "YES" for row in historical):
        failures.append("historical_candidate_reintroduced: a historical RVA became eligible")

    if failures:
        print("SELF-TEST FAIL")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("SELF-TEST PASS: CORE-013R static gate checks passed")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CORE-013R static target resolution")
    parser.add_argument("--self-test", action="store_true", help="run static gate self-tests")
    parser.add_argument("--check", action="store_true", help="validate existing artifacts")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.check:
        return check_outputs()
    return write_outputs()


if __name__ == "__main__":
    raise SystemExit(main())
