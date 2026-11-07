from __future__ import annotations

"""CORE-013 / E-012-01 target gate.

The CORE-013 experiment is allowed only when exe_core012_next_experiment.csv
contains exactly one row, experiment_id=E-012-01, and one explicit EXE RVA.

The frozen CORE-012 row does not satisfy the last condition: its
target_candidate is an EXE .text census plus eight attribution addresses.
This tool therefore fails closed with E01201_TARGET_UNRESOLVED.  It performs
no process launch and writes no fabricated execution observation.

Run:
    python core013_e01201.py
    python core013_e01201.py --self-test
    python core013_e01201.py --check
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

EXE = ROOT / "COD OL" / "codoMP_client_shipRetail.exe"
EXE_SHA256 = "36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537"
IMAGE_BASE = 0x00400000

CORE012_ENTRY = ROOT / "exe_core012_entry_candidates.csv"
CORE012_STATE = ROOT / "exe_core012_minimum_state.csv"
CORE012_MODELS = ROOT / "exe_core012_boundary_models.csv"
CORE012_GAPS = ROOT / "exe_core012_gap_list.csv"
CORE012_NEXT = ROOT / "exe_core012_next_experiment.csv"
CORE012_DESIGN = ROOT / "CODOL_STANDALONE_CORE_012_BOOTSTRAP_DESIGN.md"

CORE011_DECISION = ROOT / "exe_core011_decision.csv"
CORE011_RUNS = ROOT / "exe_core011_runs.csv"
CORE011_REPORT = ROOT / "CODOL_STANDALONE_CORE_011_POST_BOUNDARY_EXECUTION.md"
CORE010_REPORT = ROOT / "CODOL_STANDALONE_CORE_010_BOOTSTRAP_CONTRACT.md"
CORE009_REPORT = ROOT / "CODOL_STANDALONE_CORE_009_BOUNDARY_OBSERVATION.md"

RESULT_MD = ROOT / "CODOL_STANDALONE_CORE_013_E01201_RESULT.md"
RUNS_CSV = ROOT / "exe_core013_runs.csv"
HITS_CSV = ROOT / "exe_core013_candidate_hits.csv"
STATE_CSV = ROOT / "exe_core013_state_observation.csv"
CONTROL_CSV = ROOT / "exe_core013_control_transfer.csv"
DECISION_CSV = ROOT / "exe_core013_decision.csv"

GENERATED_PATHS = (RESULT_MD, RUNS_CSV, HITS_CSV, STATE_CSV, CONTROL_CSV, DECISION_CSV)

# Hashes are of the frozen CORE-009/010/011/012 inputs.  They are intentionally
# explicit so a changed input stops the experiment before any output is written.
FROZEN_SHA256 = {
    CORE012_ENTRY.name: "8FD126BD444E5DA1192CEF8A51E83CF8A963834971DD3F937E4118F3F71473CF",
    CORE012_STATE.name: "A9CF3E6BBEA2042DFD5484332405ED1BDCA9500215CDF6C9965A82A3E6442969",
    CORE012_MODELS.name: "F06D57A9467C623D092E9C34A36931AABA1045C62BD2B14E7EB0D69EFA3D7F02",
    CORE012_GAPS.name: "77FE2B3F151F8D97902A29FAF70648921DBB8C17668058AA99251085D50F5F18",
    CORE012_NEXT.name: "AC9E58B72E61AAF77297FA4AE3A63381136ED510E710ADB7B89D00739E37FB23",
    CORE012_DESIGN.name: "5200960EE3BE97DAF50528343992ED08E211D729127D54E068830DD559622BAE",
    CORE011_DECISION.name: "F3B0CE964534FC99F16F17BB478ADAE0A2FB7CE856D7A82E1138E4FCEBA96E4B",
    CORE011_RUNS.name: "CD162CC2DC93CBD71CBB908D1F511634003E03763D1940B5998571EFF6DA23E7",
    CORE011_REPORT.name: "6A12BA7C330196D758C15C6D01786F32135B466B18B249E512383102416816A2",
    CORE010_REPORT.name: "8189C8F0C75E8594BBEFB5A04574E03D09ED6ECE428FEBDF90CA01C45CFDB8D8",
    CORE009_REPORT.name: "8ED51612A6A8DB39E23C47294A576962B4C553880D683F1F49342DCEFD7D1ECC",
}

EXPECTED_ROWS = {
    CORE012_ENTRY.name: 12,
    CORE012_STATE.name: 16,
    CORE012_MODELS.name: 2,
    CORE012_GAPS.name: 15,
    CORE012_NEXT.name: 1,
    CORE011_RUNS.name: 4,
}
EXPECTED_CANDIDATE_COUNT = 12

EXPECTED_EXPERIMENT_ID = "E-012-01"
EXPECTED_TARGET_MARKER = "E01201_TARGET_UNRESOLVED"
EXPECTED_CORE011_VERDICT = "NOT_OBSERVED"
EXPECTED_CORE012_STATUS = "STANDALONE_BOOTSTRAP_ENTRY = CANDIDATE"

NEXT_FIELDS = {
    "experiment_id",
    "purpose",
    "single_variable",
    "target_candidate",
    "method",
    "success_criterion",
    "stop_condition",
    "read_only",
    "reversible",
    "binary_modification",
    "dll_modification",
    "tencent_component_modification",
}

RUN_FIELDS = [
    "run_id",
    "experiment_id",
    "run_label",
    "command_line",
    "process_start_timestamp",
    "ordinal1_timestamp",
    "candidate_timestamp",
    "candidate_after_ordinal1",
    "ordinal1_observed",
    "candidate_phase",
    "process_state",
    "status",
]

HIT_FIELDS = [
    "run_id",
    "experiment_id",
    "candidate_rva",
    "candidate_va",
    "module",
    "thread_id",
    "timestamp",
    "ordinal1_timestamp",
    "phase",
    "hit_count",
    "status",
]

STATE_FIELDS = [
    "run_id",
    "experiment_id",
    "field",
    "expected",
    "observed",
    "status",
]

CONTROL_FIELDS = [
    "run_id",
    "experiment_id",
    "candidate_rva",
    "instruction",
    "next_target",
    "classification",
    "status",
]

DECISION_FIELDS = [
    "item",
    "value",
]

REQUIRED_DRIFT_KEYS = (
    "target_drift",
    "experiment_count_drift",
    "candidate_count_drift",
    "core011_verdict_drift",
    "core012_status_drift",
    "external_dependency_drift",
)


class ValidationError(RuntimeError):
    """Raised when a fixed input violates the CORE-013 gate."""


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


def parse_target_rvas(text: str) -> list[int]:
    """Return explicit EXE RVA tokens.

    A bare whole-section phrase is not a target.  Only 0x-prefixed address
    tokens qualify.  This makes the frozen CORE-012 census fail closed while
    still recognizing a future one-RVA record.
    """

    return [int(token, 16) for token in re.findall(r"0x[0-9A-Fa-f]+", text)]


def validate_inputs() -> tuple[dict[str, list[dict[str, str]]], dict[str, object]]:
    missing = [path.name for path in (
        CORE012_ENTRY, CORE012_STATE, CORE012_MODELS, CORE012_GAPS,
        CORE012_NEXT, CORE012_DESIGN, CORE011_DECISION, CORE011_RUNS,
        CORE011_REPORT, CORE010_REPORT, CORE009_REPORT, EXE,
    ) if not path.is_file()]
    if missing:
        raise ValidationError("missing fixed input(s): " + ", ".join(missing))

    actual_hashes = {path.name: sha256(path) for path in (
        CORE012_ENTRY, CORE012_STATE, CORE012_MODELS, CORE012_GAPS,
        CORE012_NEXT, CORE012_DESIGN, CORE011_DECISION, CORE011_RUNS,
        CORE011_REPORT, CORE010_REPORT, CORE009_REPORT,
    )}
    hash_errors = [
        f"{name}: expected {expected}, found {actual_hashes.get(name)}"
        for name, expected in FROZEN_SHA256.items()
        if actual_hashes.get(name) != expected
    ]
    if hash_errors:
        raise ValidationError("frozen-input SHA-256 drift: " + "; ".join(hash_errors))

    if sha256(EXE) != EXE_SHA256:
        raise ValidationError(
            f"target EXE SHA-256 drift: expected {EXE_SHA256}, found {sha256(EXE)}"
        )

    loaded = {
        CORE012_ENTRY.name: read_csv(CORE012_ENTRY),
        CORE012_STATE.name: read_csv(CORE012_STATE),
        CORE012_MODELS.name: read_csv(CORE012_MODELS),
        CORE012_GAPS.name: read_csv(CORE012_GAPS),
        CORE012_NEXT.name: read_csv(CORE012_NEXT),
        CORE011_RUNS.name: read_csv(CORE011_RUNS),
    }
    next_rows = loaded[CORE012_NEXT.name]
    if len(next_rows) != 1:
        raise ValidationError(
            f"experiment_count_drift: expected exactly one next-experiment row, found {len(next_rows)}"
        )
    next_row = next_rows[0]
    if set(next_row) != NEXT_FIELDS:
        raise ValidationError(
            "next-experiment schema drift: "
            + f"expected {sorted(NEXT_FIELDS)}, found {sorted(next_row)}"
        )
    if next_row.get("experiment_id") != EXPECTED_EXPERIMENT_ID:
        raise ValidationError(
            "experiment id drift: "
            + f"expected {EXPECTED_EXPERIMENT_ID}, found {next_row.get('experiment_id')!r}"
        )

    candidate_rows = loaded[CORE012_ENTRY.name]
    candidate_ids = [row.get("candidate_id", "") for row in candidate_rows]
    if len(candidate_ids) != EXPECTED_CANDIDATE_COUNT or len(set(candidate_ids)) != EXPECTED_CANDIDATE_COUNT:
        raise ValidationError(
            "candidate_count_drift: expected "
            f"{EXPECTED_CANDIDATE_COUNT} unique CORE-012 candidate rows, "
            f"found {len(candidate_ids)} rows / {len(set(candidate_ids))} unique ids"
        )

    row_errors = [
        f"{name}: expected {expected} rows, found {len(loaded[name])}"
        for name, expected in EXPECTED_ROWS.items()
        if len(loaded[name]) != expected
    ]
    if row_errors:
        raise ValidationError("row-count drift: " + "; ".join(row_errors))

    core011 = {
        row["item"]: row["value"]
        for row in read_csv(CORE011_DECISION)
        if row.get("item")
    }
    if core011.get("EXE_IMAGE_EXECUTION_AFTER_BOUNDARY") != EXPECTED_CORE011_VERDICT:
        raise ValidationError(
            "core011_verdict_drift: EXE_IMAGE_EXECUTION_AFTER_BOUNDARY="
            f"{core011.get('EXE_IMAGE_EXECUTION_AFTER_BOUNDARY')!r}"
        )

    design_text = CORE012_DESIGN.read_text(encoding="utf-8")
    if EXPECTED_CORE012_STATUS not in design_text:
        raise ValidationError(
            f"core012_status_drift: missing {EXPECTED_CORE012_STATUS!r}"
        )

    state_text = CORE012_STATE.read_text(encoding="utf-8-sig")
    tencent_rows = [
        row for row in loaded[CORE012_STATE.name]
        if row.get("item", "").startswith("Tencent launcher")
    ]
    if (
        len(tencent_rows) != 1
        or tencent_rows[0].get("required_for_standalone") != "NO"
        or "NOT_REQUIRED_CONFIRMED" not in tencent_rows[0].get("evidence_grade", "")
    ):
        raise ValidationError(
            "external_dependency_drift: Tencent launcher components are not "
            "NO/NOT_REQUIRED_CONFIRMED"
        )
    if "Zero-Tencent native boot reached TenProxy/project DLL load stage" not in state_text:
        raise ValidationError(
            "external_dependency_drift: CORE-012 external-dependency evidence is missing"
        )

    target_text = next_row.get("target_candidate", "")
    target_rvas = parse_target_rvas(target_text)
    target_ok = len(target_rvas) == 1 and "EXE .text section as a whole" not in target_text
    if not target_ok:
        raise ValidationError(
            "target_drift: E-012-01 does not specify exactly one explicit EXE RVA target; "
            f"target_candidate={target_text!r}"
        )

    # This point is deliberately unreachable for the frozen CORE-012 input.
    run_specs = (
        ("Run A", "baseline standalone command line", ""),
        ("Run B", "-q", "-q"),
    )
    return loaded, {
        "next_row": next_row,
        "target_rva": target_rvas[0],
        "run_specs": run_specs,
        "core011": core011,
    }


def unresolved_rows() -> tuple[list[dict[str, object]], list[dict[str, object]],
                                list[dict[str, object]], list[dict[str, object]]]:
    reasons = {
        "target_drift": "UNRESOLVED: target_candidate spans EXE .text and names eight RVAs",
        "experiment_count_drift": "PASS: exactly 1 row and experiment_id=E-012-01",
        "candidate_count_drift": "PASS: exactly 12 unique CORE-012 candidate rows; no new candidate created",
        "core011_verdict_drift": "PASS: CORE-011 remains NOT_OBSERVED",
        "core012_status_drift": "PASS: CORE-012 entry remains CANDIDATE",
        "external_dependency_drift": "PASS: Tencent launcher remains NOT_REQUIRED_CONFIRMED",
    }
    decision = [
        {"item": "FINAL_MARKER", "value": EXPECTED_TARGET_MARKER},
        {"item": "E01201_TARGET", "value": "UNRESOLVED"},
        {"item": "POST_BOUNDARY_EXECUTION", "value": "NOT_OBSERVED"},
        {"item": "MINIMUM_STATE", "value": "UNKNOWN"},
        {"item": "NEXT_TRACK", "value": "STANDALONE_ENTRY_UNRESOLVED"},
        {"item": "STOP_CONDITION", "value": "STOP-3"},
        {"item": "RUNS_EXECUTED", "value": "0"},
        {"item": "PROCESS_LAUNCHED", "value": "NO"},
        {"item": "EXPERIMENT_ROWS", "value": "1"},
        {"item": "CANDIDATE_ROWS", "value": str(EXPECTED_CANDIDATE_COUNT)},
        {"item": "BINARY_MODIFICATION", "value": "NO"},
        {"item": "DLL_MODIFICATION", "value": "NO"},
    ]
    for key in REQUIRED_DRIFT_KEYS:
        decision.append({"item": key, "value": reasons[key]})
    return [], [], [], decision


def result_markdown(decision: list[dict[str, object]]) -> str:
    values = {str(row["item"]): str(row["value"]) for row in decision}
    return f"""# CODOL_STANDALONE_CORE_013_E01201_RESULT

## Outcome

```text
FINAL_MARKER = {values['FINAL_MARKER']}
E01201_TARGET = {values['E01201_TARGET']}
POST_BOUNDARY_EXECUTION = {values['POST_BOUNDARY_EXECUTION']}
MINIMUM_STATE = {values['MINIMUM_STATE']}
NEXT_TRACK = {values['NEXT_TRACK']}
```

## Gate

CORE-013 requires `exe_core012_next_experiment.csv` to identify exactly one
explicit EXE RVA before any dynamic observation starts.  The frozen
`E-012-01` row instead specifies the EXE `.text` section as a whole and lists
eight attribution addresses.  CORE-013 STOP-3 therefore applies.

No process was launched.  No candidate was selected or substituted.  No EXE,
DLL, `.tvm0` file, hook, patch, or Tencent component was modified or inspected
internally.

## Evidence

```text
target_candidate = EXE .text section as a whole
attribution_rvas = 0x77F580 / 0x4FD9B0 / 0x4FCEE0 / 0x808650 /
                   0x7E98F0 / 0x6212C0 / 0x00561133 / 0x37FA70
required_unique_target_count = 1
resolved_unique_target_count = 0
```

The CORE-012 candidate remains `CANDIDATE`.  This result does not rewrite it
to `NOT_FOUND`, and it does not claim dynamic reachability.

## Stop Condition

`STOP-3 TARGET_UNRESOLVED`: stop without manufacturing a candidate or running
a widened census.
"""


def render_artifacts() -> dict[Path, bytes]:
    runs, hits, states, decision = unresolved_rows()
    payloads: dict[Path, bytes] = {
        RUNS_CSV: csv_bytes(RUN_FIELDS, runs),
        HITS_CSV: csv_bytes(HIT_FIELDS, hits),
        STATE_CSV: csv_bytes(STATE_FIELDS, states),
        CONTROL_CSV: csv_bytes(CONTROL_FIELDS, []),
        DECISION_CSV: csv_bytes(DECISION_FIELDS, decision),
        RESULT_MD: result_markdown(decision).encode("utf-8"),
    }
    return payloads


def validate_rendered(payloads: dict[Path, bytes]) -> list[str]:
    errors: list[str] = []
    if set(payloads) != set(GENERATED_PATHS):
        errors.append("artifact set drift")
    for path, payload in payloads.items():
        if path.suffix == ".csv":
            text = payload.decode("utf-8-sig")
            rows = list(csv.DictReader(io.StringIO(text)))
            if path in (RUNS_CSV, HITS_CSV, STATE_CSV, CONTROL_CSV) and rows:
                errors.append(f"{path.name}: unresolved target must have zero data rows")
            if path == DECISION_CSV:
                items = {row["item"] for row in rows}
                if "FINAL_MARKER" not in items or not set(REQUIRED_DRIFT_KEYS).issubset(items):
                    errors.append("decision artifact is missing gate or drift fields")
                marker = next((row["value"] for row in rows if row["item"] == "FINAL_MARKER"), "")
                if marker != EXPECTED_TARGET_MARKER:
                    errors.append(f"decision marker drift: {marker!r}")
    return errors


def artifact_diff(payloads: dict[Path, bytes]) -> list[str]:
    errors: list[str] = []
    for path, payload in payloads.items():
        if not path.is_file():
            errors.append(f"missing artifact: {path.name}")
        elif path.read_bytes() != payload:
            errors.append(f"artifact drift: {path.name}")
    return errors


def write_atomic(payloads: dict[Path, bytes]) -> None:
    """Write all outputs with rollback on failure; never leave a partial set."""

    backups: dict[Path, bytes | None] = {}
    written: list[Path] = []
    try:
        for path, payload in payloads.items():
            backups[path] = path.read_bytes() if path.is_file() else None
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp",
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


def command_line_for(run_spec: tuple[str, str, str]) -> str:
    _label, _description, arg = run_spec
    command = f'"{EXE}"'
    return command if not arg else command + " " + arg


def live_rows(config: dict[str, object]) -> tuple[
        list[dict[str, object]], list[dict[str, object]],
        list[dict[str, object]], list[dict[str, object]]]:
    """Reserved for the future one-target path.

    The frozen CORE-012 target is unresolved, so this function must not run
    until a replacement CORE-012 artifact explicitly identifies one RVA.
    """

    raise ValidationError(
        "dynamic observer path is disabled until exactly one explicit EXE RVA "
        "is frozen in CORE-012 next_experiment"
    )


def preflight() -> tuple[bool, str]:
    try:
        validate_inputs()
    except ValidationError as exc:
        message = str(exc)
        if "target_drift" in message:
            return False, message
        raise
    return True, "E-012-01 has one explicit EXE RVA target"


def run_generator() -> int:
    try:
        resolved, message = preflight()
    except ValidationError as exc:
        print(f"VALIDATION FAIL: {exc}", file=sys.stderr)
        return 1

    if resolved:
        print("VALIDATION PASS: one explicit target is available")
        print("Observer execution is not implemented in this frozen-state build.")
        return 1

    print("VALIDATION PASS: fixed inputs are intact")
    print(f"STOP-3: {message}")
    print(f"FINAL_MARKER={EXPECTED_TARGET_MARKER}")

    payloads = render_artifacts()
    errors = validate_rendered(payloads)
    if errors:
        print("VALIDATION FAIL: rendered artifacts are invalid", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    write_atomic(payloads)
    post_errors = artifact_diff(payloads)
    if post_errors:
        print("VALIDATION FAIL: post-write reread failed", file=sys.stderr)
        for error in post_errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print("ARTIFACTS: written and reread successfully")
    return 0


def check_artifacts() -> int:
    try:
        validate_inputs()
    except ValidationError as exc:
        message = str(exc)
        if "target_drift" not in message:
            print(f"VALIDATION FAIL: {exc}", file=sys.stderr)
            return 1

    payloads = render_artifacts()
    errors = validate_rendered(payloads) + artifact_diff(payloads)
    print(f"VALIDATION {'PASS' if not errors else 'FAIL'}: CORE-013 artifacts")
    for error in errors:
        print(f"  - {error}", file=sys.stderr)
    return 0 if not errors else 1


def self_test() -> int:
    """Exercise all required drift detectors without touching deliverables."""

    failures: list[str] = []

    def expect_error(name: str, mutate) -> None:
        original_read_csv = globals()["read_csv"]
        original_sha = globals()["sha256"]
        original_read_text = Path.read_text
        original_read_bytes = Path.read_bytes
        try:
            def fake_read(path: Path):
                rows = original_read_csv(path)
                return mutate(path, rows) if mutate else rows

            def fake_sha(path: Path) -> str:
                return original_sha(path)

            globals()["read_csv"] = fake_read
            globals()["sha256"] = fake_sha
            try:
                validate_inputs()
            except ValidationError as exc:
                message = str(exc)
                if name not in message:
                    failures.append(f"{name}: raised non-matching error: {exc}")
            else:
                failures.append(f"{name}: mutation was not detected")
        finally:
            globals()["read_csv"] = original_read_csv
            globals()["sha256"] = original_sha
            Path.read_text = original_read_text
            Path.read_bytes = original_read_bytes

    def core011_verdict_drift(path: Path, rows: list[dict[str, str]]):
        if path == CORE011_DECISION:
            for row in rows:
                if row.get("item") == "EXE_IMAGE_EXECUTION_AFTER_BOUNDARY":
                    row["value"] = "OBSERVED"
        return rows

    def target_drift(path: Path, rows: list[dict[str, str]]):
        if path == CORE012_NEXT:
            rows[0]["target_candidate"] = "EXE .text section as a whole"
        return rows

    def experiment_count_drift(path: Path, rows: list[dict[str, str]]):
        if path == CORE012_NEXT:
            return rows + [dict(rows[0])]
        return rows

    def candidate_count_drift(path: Path, rows: list[dict[str, str]]):
        if path == CORE012_ENTRY:
            return rows[:-1]
        return rows

    def core012_status_drift(path: Path, rows: list[dict[str, str]]):
        return rows

    def external_dependency_drift(path: Path, rows: list[dict[str, str]]):
        if path == CORE012_STATE:
            for row in rows:
                if row.get("item", "").startswith("Tencent launcher"):
                    row["required_for_standalone"] = "YES"
        return rows

    expect_error("target_drift", target_drift)
    expect_error("experiment_count_drift", experiment_count_drift)
    expect_error("candidate_count_drift", candidate_count_drift)
    expect_error("core011_verdict_drift", core011_verdict_drift)
    expect_error("external_dependency_drift", external_dependency_drift)

    def core012_status_drift_impl() -> None:
        original_sha = globals()["sha256"]
        original_read_text = Path.read_text
        try:
            def fake_read_text(self: Path, *args, **kwargs):
                if self == CORE012_DESIGN:
                    return original_read_text(self, *args, **kwargs).replace(
                        EXPECTED_CORE012_STATUS,
                        "STANDALONE_BOOTSTRAP_ENTRY = CONFIRMED",
                    )
                return original_read_text(self, *args, **kwargs)

            def fake_sha(path: Path) -> str:
                if path == CORE012_DESIGN:
                    return FROZEN_SHA256[CORE012_DESIGN.name]
                return original_sha(path)

            globals()["sha256"] = fake_sha
            Path.read_text = fake_read_text
            try:
                validate_inputs()
            except ValidationError as exc:
                if "core012_status_drift" not in str(exc):
                    failures.append(f"core012_status_drift: raised non-matching error: {exc}")
            else:
                failures.append("core012_status_drift: mutation was not detected")
        finally:
            globals()["sha256"] = original_sha
            Path.read_text = original_read_text

    core012_status_drift_impl()

    if failures:
        print("SELF-TEST FAIL")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("SELF-TEST PASS: target/experiment/candidate/CORE-011/CORE-012/dependency drift detected")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CORE-013 E-012-01 target gate")
    parser.add_argument("--self-test", action="store_true", help="exercise drift detectors")
    parser.add_argument("--check", action="store_true", help="validate existing artifacts")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.check:
        return check_artifacts()
    return run_generator()


if __name__ == "__main__":
    raise SystemExit(main())
