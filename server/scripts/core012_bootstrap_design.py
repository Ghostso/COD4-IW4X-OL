from __future__ import annotations

"""CODOL_STANDALONE_CORE_012 - Standalone Bootstrap Design (evidence-locked).

Turns the frozen CORE-001..011 evidence base into an implementation design:
EXE runtime-entry inventory, standalone minimum state, two Base ordinal-1
boundary replacement models (facts only, no winner), the gap list, and
exactly ONE next experiment (E-012-01).

Rules enforced by validate():
  * the only primary object is codoMP_client_shipRetail.exe (SHA-256
    re-verified; PE headers, entry bytes and IAT slot re-decoded read-only);
  * Base.dll ordinal-1 stays an EXTERNAL BOUNDARY - no .tvm0 and no
    Base/TenProxy/TCLS/WeGame internals are claimed anywhere;
  * no EXE/DLL patch, hook, stub or replacement - the sample is only READ;
  * the CORE-011 verdict is load-bearing: EXE_IMAGE_EXECUTION_AFTER_BOUNDARY
    must stay NOT_OBSERVED, so no candidate may be recorded as post-ordinal-1
    OBSERVED and no native entry may be upgraded to CONFIRMED;
  * the 0x0849B500 static writer stays NOT_FOUND (the old-report error is
    not re-introduced);
  * final status stays: entry CANDIDATE / minimum state PARTIAL /
    boundary models DEFINED / next experiment E-012-01.

Tooling: python core012_bootstrap_design.py
"""

import csv
import hashlib
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXE = ROOT / "COD OL" / "codoMP_client_shipRetail.exe"
MD_OUT = ROOT / "CODOL_STANDALONE_CORE_012_BOOTSTRAP_DESIGN.md"

EXE_SHA256 = "36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537"
IMAGE_BASE = 0x00400000
ENTRY_RVA = 0x0E5DC690
ENTRY_BYTES = "FF 15 65 C6 9D 0E"
IAT_SLOT_RVA = 0x0E5DC665
IAT_SLOT_VA = 0x0E9DC665          # the FF 15 encodes this absolute slot address
EXE_RETURN_RVA = 0x0E5DC696       # zero padding: no native fall-through

CSV_NAMES = {
    "ENTRY": "exe_core012_entry_candidates.csv",
    "STATE": "exe_core012_minimum_state.csv",
    "MODELS": "exe_core012_boundary_models.csv",
    "GAPS": "exe_core012_gap_list.csv",
    "NEXT": "exe_core012_next_experiment.csv",
}

EXPECTED_ROWS = {"ENTRY": 12, "STATE": 16, "MODELS": 2, "GAPS": 15, "NEXT": 1}

REQUIRED_INPUTS = (
    "CODOL_STANDALONE_CORE_009_BOUNDARY_OBSERVATION.md",
    "CODOL_STANDALONE_CORE_010_BOOTSTRAP_CONTRACT.md",
    "CODOL_STANDALONE_CORE_011_POST_BOUNDARY_EXECUTION.md",
    "exe_core010_gap_list.csv",
    "exe_core010_contract_matrix.csv",
    "exe_core011_decision.csv",
    "exe_core011_runs.csv",
    "CODOL_EX020_ENGINE_CANDIDATES.md",
    "CODOL_EX026_ZERO_TENCENT_NATIVE_BOOT.md",
    "CODOL_EX028_OBSERVER_DIVERGENCE.md",
    "CODOL_EX031_WIN_NO_TCLS_RUNTIME_PREDICATE.md",
    "CODOL_EX032_ARGV_PROVIDER_SEMANTICS.md",
    "CODOL_EX035_Q_QA_GATE_AND_BOOTSTRAP.md",
    "CODOL_EX041_POST_GATE_BOOTSTRAP_STATE_MACHINE.md",
    "CODOL_EX042_849413B_POST_GATE_CONSUMERS.md",
    "CODOL_EX045_NATIVE_BOOTSTRAP_DISPATCHER_CHAIN.md",
    "CODOL_EX046_NATIVE_BOOTSTRAP_TENCENT_DEPENDENCY_ANALYSIS.md",
    "CODOL_EX057_IIPS_RUNTIME_BOUNDARY.md",
    "CODOL_EX065_TCLS_UPSTREAM_BOUNDARY.md",
)

HISTORICAL_CHAIN_RVAS = (
    "0x77F580", "0x77F8B3", "0x4FD9B0", "0x4FCEE0", "0x808650", "0x7E98F0", "0x6212C0",
)

GRADE_PREFIXES = (
    "CONFIRMED", "CANDIDATE", "UNKNOWN", "BOUNDARY", "NOT_FOUND", "NOT_OBSERVED",
    "RUNTIME_OBSERVED", "NOT_REQUIRED_CONFIRMED", "UNRESOLVED", "PACKED_OR_VM_GENERATED",
)

FINAL_STATUS = (
    "STANDALONE_BOOTSTRAP_ENTRY = CANDIDATE",
    "STANDALONE_MINIMUM_STATE = PARTIAL",
    "BOUNDARY_REPLACEMENT_MODEL = DEFINED",
    "NEXT_EXPERIMENT = E-012-01",
    "FINAL_MARKER = STANDALONE_BOOTSTRAP_DESIGN_CANDIDATE",
)


class Image:
    """Minimal read-only PE32 view of the sample (same discipline as CORE-010)."""

    def __init__(self, blob: bytes) -> None:
        self.blob = blob
        self.pe = struct.unpack_from("<I", blob, 0x3C)[0]
        assert blob[self.pe : self.pe + 4] == b"PE" + bytes(2), "not a PE file"
        coff = self.pe + 4
        (self.machine,) = struct.unpack_from("<H", blob, coff)
        (self.nsections,) = struct.unpack_from("<H", blob, coff + 2)
        (self.opt_size,) = struct.unpack_from("<H", blob, coff + 16)
        self.opt = coff + 20
        (self.magic,) = struct.unpack_from("<H", blob, self.opt)
        (self.entry_rva,) = struct.unpack_from("<I", blob, self.opt + 16)
        (self.image_base,) = struct.unpack_from("<I", blob, self.opt + 28)
        self.ddir = self.opt + (96 if self.magic == 0x10B else 112)
        self.sections: list[tuple[str, int, int, int, int]] = []
        sec = self.opt + self.opt_size
        for i in range(self.nsections):
            off = sec + i * 40
            name = blob[off : off + 8].rstrip(bytes(1)).decode("latin-1")
            vsize, vaddr, rawsize, rawptr = struct.unpack_from("<IIII", blob, off + 8)
            self.sections.append((name, vaddr, vsize, rawptr, rawsize))

    def rva_to_off(self, rva: int) -> int | None:
        for _name, vaddr, vsize, rawptr, rawsize in self.sections:
            if vaddr <= rva < vaddr + max(vsize, rawsize):
                return rawptr + (rva - vaddr)
        return None

    def read_rva(self, rva: int, size: int) -> bytes:
        off = self.rva_to_off(rva)
        assert off is not None, f"unmapped rva {rva:#x}"
        return self.blob[off : off + size]

    def directory(self, index: int) -> tuple[int, int]:
        return struct.unpack_from("<II", self.blob, self.ddir + index * 8)

    def imports(self) -> list[tuple[str, int, int]]:
        rva, _size = self.directory(1)
        out: list[tuple[str, int, int]] = []
        if not rva:
            return out
        cur = rva
        while True:
            off = self.rva_to_off(cur)
            desc = self.blob[off : off + 20]
            if len(desc) < 20 or desc == bytes(20):
                break
            (orig,) = struct.unpack_from("<I", desc)
            (name_rva,) = struct.unpack_from("<I", desc, 12)
            (first,) = struct.unpack_from("<I", desc, 16)
            noff = self.rva_to_off(name_rva)
            end = self.blob.index(bytes(1), noff)
            out.append((self.blob[noff:end].decode("latin-1"), orig, first))
            cur += 20
        return out


def find_all(blob: bytes, needle: bytes) -> list[int]:
    out: list[int] = []
    start = 0
    while True:
        pos = blob.find(needle, start)
        if pos < 0:
            break
        out.append(pos)
        start = pos + 1
    return out


def read_csv(name: str) -> list[dict[str, str]]:
    path = ROOT / name
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(name: str, fields: list[str], rows: list[dict[str, object]]) -> Path:
    path = ROOT / name
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def verify_static() -> dict[str, object]:
    """Read-only re-validation of every static claim CORE-012 relies on."""
    blob = EXE.read_bytes()
    img = Image(blob)
    st: dict[str, object] = {}
    st["exe_size"] = len(blob)
    st["exe_sha256"] = hashlib.sha256(blob).hexdigest().upper()
    st["machine"] = img.machine
    st["magic"] = img.magic
    st["image_base"] = img.image_base
    st["entry_rva"] = img.entry_rva
    st["entry_bytes"] = img.read_rva(img.entry_rva, 6).hex(" ").upper()
    (slot,) = struct.unpack_from("<I", blob, img.rva_to_off(IAT_SLOT_RVA))
    st["iat_slot_value"] = slot
    st["import_names"] = [name for name, _ilt, _iat in img.imports()]
    _rel_rva, rel_size = img.directory(5)
    st["reloc_dir_size"] = rel_size
    eoff = img.rva_to_off(img.entry_rva)
    span = 0
    while blob[eoff + 6 + span] == 0 and span < 0x4000:
        span += 1
    st["entry_fallthrough_zero_span"] = span
    st["gate_tokens"] = {
        token.decode("latin-1"): len(find_all(blob, token))
        for token in (b"-qa", b"-src=tgp", b"WIN_NO_TCLS")
    }
    return st


def check_static(st: dict[str, object]) -> list[str]:
    errors: list[str] = []
    if st["exe_sha256"] != EXE_SHA256:
        errors.append(f"EXE SHA-256 mismatch: {st['exe_sha256']}")
    if st["machine"] != 0x14C:
        errors.append(f"machine is not I386: 0x{st['machine']:X}")
    if st["magic"] != 0x10B:
        errors.append(f"optional header is not PE32: 0x{st['magic']:X}")
    if st["image_base"] != IMAGE_BASE:
        errors.append(f"ImageBase mismatch: 0x{st['image_base']:X}")
    if st["entry_rva"] != ENTRY_RVA:
        errors.append(f"Entry RVA mismatch: 0x{st['entry_rva']:X}")
    if st["entry_bytes"] != ENTRY_BYTES:
        errors.append(f"entry bytes mismatch: {st['entry_bytes']}")
    if st["iat_slot_value"] != 0x80000001:
        errors.append(f"IAT slot 0x{IAT_SLOT_VA:X} is not Base ordinal 1: 0x{st['iat_slot_value']:08X}")
    if st["import_names"] != ["codoMP_client_shipRetailBase.dll"]:
        errors.append(f"import descriptor mismatch: {st['import_names']}")
    if st["reloc_dir_size"] != 0:
        errors.append(f"base relocation directory not empty: {st['reloc_dir_size']}")
    if st["entry_fallthrough_zero_span"] < 2000:
        errors.append(f"entry fall-through zero span too small: {st['entry_fallthrough_zero_span']}")
    for token, count in st["gate_tokens"].items():
        if count < 1:
            errors.append(f"gate token {token!r} not found in file image")
    return errors


def check_inputs() -> list[str]:
    return [f"required input artifact missing: {name}" for name in REQUIRED_INPUTS if not (ROOT / name).is_file()]


def check_core011() -> list[str]:
    """The CORE-011 verdict is load-bearing; refuse to build on an upgraded one."""
    errors: list[str] = []
    rows = {row["item"]: row["value"] for row in read_csv("exe_core011_decision.csv")}
    if rows.get("EXE_IMAGE_EXECUTION_AFTER_BOUNDARY") != "NOT_OBSERVED":
        errors.append("CORE-011 verdict changed: EXE_IMAGE_EXECUTION_AFTER_BOUNDARY must stay NOT_OBSERVED")
    if rows.get("ENVIRONMENT_DEPENDENT") != "NO":
        errors.append("CORE-011 verdict changed: ENVIRONMENT_DEPENDENT must stay NO")
    if rows.get("post_boundary_candidate_hits") != "0":
        errors.append("CORE-011 verdict changed: post_boundary_candidate_hits must stay 0")
    return errors


def grade_ok(value: str) -> bool:
    return any(value.startswith(prefix) for prefix in GRADE_PREFIXES)


def embedded_rows() -> dict[str, list[dict[str, str]]]:
    """The frozen artifacts this generator is designed to reproduce."""
    return {"ENTRY": ROWS_ENTRY, "STATE": ROWS_STATE, "MODELS": ROWS_MODELS,
            "GAPS": ROWS_GAPS, "NEXT": ROWS_NEXT}


def load_artifacts() -> dict[str, list[dict[str, str]]]:
    """Load the artifacts as they currently exist on disk.

    The validator must judge the on-disk state (which is what a reviewer will
    read), not the embedded constants - otherwise any hand edit silently
    escapes every rule below.
    """
    return {key: read_csv(name) for key, name in CSV_NAMES.items()}


def artifact_agreement(embedded: dict, on_disk: dict) -> list[str]:
    """Report row/field differences between embedded design and on-disk files."""
    errors: list[str] = []
    for key in ("ENTRY", "STATE", "MODELS", "GAPS", "NEXT"):
        emb, disk = embedded[key], on_disk[key]
        if emb != disk:
            if len(emb) != len(disk):
                errors.append(
                    f"{CSV_NAMES[key]}: on-disk row count {len(disk)} != designed {len(emb)}"
                )
            else:
                diff = next(
                    (i for i, (a, b) in enumerate(zip(disk, emb)) if a != b), None
                )
                errors.append(
                    f"{CSV_NAMES[key]}: on-disk content differs from design at row {diff}"
                )
    if not MD_OUT.is_file():
        errors.append(f"{MD_OUT.name} is missing")
    elif MD_OUT.read_bytes().decode("utf-8") != MD_TEXT:
        errors.append(f"{MD_OUT.name}: on-disk content differs from design")
    return errors


def data_input_errors() -> list[str]:
    """Independent corroboration: the on-disk files must still agree with the
    frozen evidence the design cites (CORE-011 verdict)."""
    errors: list[str] = []
    rows = {row.get("item", ""): row.get("value", "") for row in read_csv("exe_core011_decision.csv")}
    if rows.get("EXE_IMAGE_EXECUTION_AFTER_BOUNDARY") != "NOT_OBSERVED":
        errors.append("CORE-011 verdict changed: EXE_IMAGE_EXECUTION_AFTER_BOUNDARY must stay NOT_OBSERVED")
    if rows.get("post_boundary_candidate_hits") != "0":
        errors.append("CORE-011 verdict changed: post_boundary_candidate_hits must stay 0")
    census = next(
        (r for r in read_csv(CSV_NAMES["NEXT"]) if r.get("experiment_id") == "E-012-01"), None
    )
    if census is None or "OBSERVED" not in census.get("success_criterion", ""):
        errors.append("E-012-01 census row lost its OBSERVED/NOT_OBSERVED success criterion")
    if rows.get("ENVIRONMENT_DEPENDENT") != "NO":
        errors.append("CORE-011 verdict changed: ENVIRONMENT_DEPENDENT must stay NO")
    return errors


FIELDS_ENTRY = ['candidate_id', 'rva', 'role', 'source', 'evidence_grade', 'call_relation', 'post_ordinal1_observed', 'tvm0_dependency', 'tencent_dependency', 'standalone_suitable', 'required_for_standalone', 'notes']
ROWS_ENTRY = [{'candidate_id': 'C012-ENTRY', 'rva': '0x0E5DC690', 'role': 'EXE Entry (single FF15 call to Base ordinal-1 IAT slot 0x0E9DC665)', 'source': 'CORE-008/010', 'evidence_grade': 'CONFIRMED', 'call_relation': 'Entry -> IAT[0x0E5DC665] -> Base.dll ordinal 1 (0x1D6582C); falls through to zero padding at 0x0E5DC696', 'post_ordinal1_observed': 'BOUNDARY', 'tvm0_dependency': 'NO (plain FF15)', 'tencent_dependency': 'NO', 'standalone_suitable': 'NO', 'required_for_standalone': 'YES', 'notes': 'Entry-adjacent anchor; no Entry-connected native continuation'}, {'candidate_id': 'C012-77F580', 'rva': '0x77F580', 'role': 'gate/bootstrap function head (0x77F580..0x77FA6F); WIN_NO_TCLS gate + 0x77F8B3 call', 'source': 'EX-045/046; CORE-010', 'evidence_grade': 'CANDIDATE (static L2 chain)', 'call_relation': 'head of historical chain; upstream caller NOT recovered', 'post_ordinal1_observed': 'NOT_OBSERVED (CORE-011 0 hits, pre+post)', 'tvm0_dependency': 'NO in chain; possible .tvm0 above caller', 'tencent_dependency': 'NO', 'standalone_suitable': 'MAYBE', 'required_for_standalone': 'UNKNOWN', 'notes': 'Chain head; entry conditions / calling convention unproven'}, {'candidate_id': 'C012-77F8B3', 'rva': '0x77F8B3', 'role': 'call site inside 0x77F580 -> 0x4FD9B0', 'source': 'EX-045', 'evidence_grade': 'CANDIDATE', 'call_relation': 'direct E8 0x77F8B3 -> 0x4FD9B0', 'post_ordinal1_observed': 'NOT_OBSERVED (CORE-011)', 'tvm0_dependency': 'NO', 'tencent_dependency': 'NO', 'standalone_suitable': 'NO', 'required_for_standalone': 'UNKNOWN', 'notes': 'Mid-function call site, not an entry'}, {'candidate_id': 'C012-4FD9B0', 'rva': '0x4FD9B0', 'role': 'bootstrap dispatcher candidate (0x4FD9B0..0x4FDADB)', 'source': 'EX-045/046', 'evidence_grade': 'CANDIDATE', 'call_relation': 'called from 0x77F8B3; calls 0x4FCEE0 at 0x4FDA03', 'post_ordinal1_observed': 'NOT_OBSERVED (CORE-011)', 'tvm0_dependency': 'NO', 'tencent_dependency': 'NO', 'standalone_suitable': 'MAYBE', 'required_for_standalone': 'UNKNOWN', 'notes': 'Multi-call dispatcher; expects gate context'}, {'candidate_id': 'C012-4FCEE0', 'rva': '0x4FCEE0', 'role': 'multi-subsystem init dispatcher (0x4FCEE0..0x4FD8DF)', 'source': 'EX-045/046', 'evidence_grade': 'CANDIDATE', 'call_relation': 'called from 0x4FDA03; calls 0x808650 at 0x4FD287', 'post_ordinal1_observed': 'NOT_OBSERVED (CORE-011)', 'tvm0_dependency': 'NO', 'tencent_dependency': 'NO', 'standalone_suitable': 'MAYBE', 'required_for_standalone': 'UNKNOWN', 'notes': 'Large init sequence; internal state assumptions unknown'}, {'candidate_id': 'C012-808650', 'rva': '0x808650', 'role': 'subsystem init wrapper (0x808650..0x808932)', 'source': 'EX-045/046', 'evidence_grade': 'CANDIDATE', 'call_relation': 'called from 0x4FD287; calls 0x7E98F0 at 0x808658', 'post_ordinal1_observed': 'NOT_OBSERVED (CORE-011)', 'tvm0_dependency': 'NO', 'tencent_dependency': 'NO', 'standalone_suitable': 'MAYBE', 'required_for_standalone': 'UNKNOWN', 'notes': 'Mid-chain wrapper'}, {'candidate_id': 'C012-7E98F0', 'rva': '0x7E98F0', 'role': 'network subsystem init (0x7E98F0..0x7E9A35)', 'source': 'EX-044/045/046', 'evidence_grade': 'CANDIDATE', 'call_relation': 'called from 0x808658; calls 0x6212C0 at 0x7E9913', 'post_ordinal1_observed': 'NOT_OBSERVED (CORE-011)', 'tvm0_dependency': 'NO', 'tencent_dependency': 'NO', 'standalone_suitable': 'MAYBE', 'required_for_standalone': 'UNKNOWN', 'notes': 'Sub-stage, not a head'}, {'candidate_id': 'C012-6212C0', 'rva': '0x6212C0', 'role': 'STUN/network mode init (0x6212C0..0x621AF5); reads 0x849413B/0x849B500', 'source': 'EX-042/043/044/045/046; CORE-010', 'evidence_grade': 'CANDIDATE (L2 static)', 'call_relation': 'called at 0x7E9913; recursive at 0x621AC6', 'post_ordinal1_observed': 'NOT_OBSERVED (CORE-011)', 'tvm0_dependency': 'NO', 'tencent_dependency': 'NO', 'standalone_suitable': 'NO', 'required_for_standalone': 'UNKNOWN', 'notes': 'Leaf-stage; selects stun1-tub.codol.qq.com vs stun.us.demonware.net'}, {'candidate_id': 'C012-00561133', 'rva': '0x00561133', 'role': 'argv provider invocation (indirect via 0x00CA827C)', 'source': 'CORE-008/010', 'evidence_grade': 'CANDIDATE', 'call_relation': 'single indirect call dword ptr [0x00CA827C]; target runtime-bound', 'post_ordinal1_observed': 'NOT_OBSERVED (argv globals still 0 at boundary entry)', 'tvm0_dependency': 'UNKNOWN', 'tencent_dependency': 'UNKNOWN', 'standalone_suitable': 'NO', 'required_for_standalone': 'UNKNOWN', 'notes': 'Indirect slot, not a code entry; binder UNKNOWN'}, {'candidate_id': 'C012-37FA70', 'rva': '0x37FA70', 'role': 'fatal error display dispatcher (WIN_NO_TCLS path)', 'source': 'EX-031/041', 'evidence_grade': 'CONFIRMED (executed for WIN_NO_TCLS in EX-031) / CANDIDATE (IIPS path)', 'call_relation': 'called from gate region -> #32770 dialog', 'post_ordinal1_observed': 'NOT_OBSERVED post-ordinal-1 in CORE-011', 'tvm0_dependency': 'UNKNOWN', 'tencent_dependency': 'NO', 'standalone_suitable': 'NO', 'required_for_standalone': 'NO', 'notes': 'Error path, not a bootstrap continuation'}, {'candidate_id': 'C012-759F50', 'rva': '0x759F50', 'role': 'structure builder fed by 0x849413B consumer at EXE+0x402423', 'source': 'EX-041/042', 'evidence_grade': 'CANDIDATE', 'call_relation': 'called with gate booleans from 0x402423 site', 'post_ordinal1_observed': 'NOT_OBSERVED', 'tvm0_dependency': 'UNKNOWN', 'tencent_dependency': 'UNKNOWN', 'standalone_suitable': 'NO', 'required_for_standalone': 'UNKNOWN', 'notes': 'Downstream consumer, not an entry'}, {'candidate_id': 'C012-ENGINE-ANCHORS', 'rva': '0x1321A9;0x239B7D;0x7036DC', 'role': 'Engine/FS/Renderer string-ref anchors', 'source': 'EX-020', 'evidence_grade': 'UNKNOWN', 'call_relation': 'no clean prologue/caller; data anchors only', 'post_ordinal1_observed': 'NOT_OBSERVED', 'tvm0_dependency': 'UNKNOWN', 'tencent_dependency': 'UNKNOWN', 'standalone_suitable': 'NO', 'required_for_standalone': 'UNKNOWN', 'notes': 'Not proven executable entries'}]

FIELDS_STATE = ['item', 'address', 'required_for_standalone', 'evidence_grade', 'source', 'notes']
ROWS_STATE = [{'item': 'EXE image loaded at ImageBase 0x00400000 (PE32/I386)', 'address': 'N/A', 'required_for_standalone': 'YES', 'evidence_grade': 'CONFIRMED', 'source': 'CORE-001/010 layer A', 'notes': 'Sample identity fixed by SHA-256'}, {'item': 'Command line containing -q or -qa (WIN_NO_TCLS bypass)', 'address': 'argv', 'required_for_standalone': 'YES', 'evidence_grade': 'CONFIRMED (gate semantics) / CANDIDATE (as requirement)', 'source': 'EX-031/035/046; CORE-010 layer A', 'notes': 'Gate token cluster EXE-owned (CORE-010)'}, {'item': 'argv count global populated', 'address': '0x0196928C', 'required_for_standalone': 'YES', 'evidence_grade': 'CONFIRMED (shape) / CANDIDATE (population mechanism)', 'source': 'CORE-009/010', 'notes': '=0 at boundary entry 12/12; write site 0x00561119 validated'}, {'item': 'argv array global populated', 'address': '0x01969290', 'required_for_standalone': 'YES', 'evidence_grade': 'CONFIRMED (shape) / CANDIDATE (population mechanism)', 'source': 'CORE-009/010', 'notes': '=0 at boundary entry 12/12; sites 0x00239C2D/0x0056111E validated'}, {'item': 'argv provider slot bound and invoked', 'address': '0x00CA827C @ call site 0x00561133', 'required_for_standalone': 'YES', 'evidence_grade': 'CANDIDATE', 'source': 'CORE-008/010; EX-032', 'notes': 'Target runtime-bound VIRTUAL_ONLY; binder UNKNOWN; holds 0x00A1517E at boundary entry'}, {'item': 'Startup gate byte = 1 (-q path)', 'address': '0x0849413B', 'required_for_standalone': 'YES', 'evidence_grade': 'CONFIRMED', 'source': 'CORE-010; EX-031/041/042', 'notes': '=0 at boundary entry; =1 at -q fatal dialog; 1 write + 3 reads validated'}, {'item': '-qa gate byte (only if -qa route)', 'address': '0x0849B500', 'required_for_standalone': 'UNKNOWN', 'evidence_grade': 'NOT_FOUND (static) / RUNTIME_OBSERVED', 'source': 'CORE-010; EX-035/042', 'notes': '0 static operand sites; read inside 0x6212C0 at 0x6213C2/0x6214D2'}, {'item': '-src=tgp gate byte (only if -src=tgp route)', 'address': '0x0849B501', 'required_for_standalone': 'UNKNOWN', 'evidence_grade': 'CONFIRMED (read) / NOT_FOUND (write)', 'source': 'CORE-010; EX-035', 'notes': '1 validated read 0x002835BA; runtime -src=tgp sets 1'}, {'item': 'Working directory = game root; full local game tree', 'address': 'process context', 'required_for_standalone': 'UNKNOWN', 'evidence_grade': 'CANDIDATE', 'source': 'EX-046 MINIMAL_CONTEXT_PARTIAL', 'notes': 'No ablation performed'}, {'item': 'System CRT/DLLs (kernel32/ntdll etc.)', 'address': 'C_RUNTIME', 'required_for_standalone': 'YES', 'evidence_grade': 'CONFIRMED', 'source': 'CORE-010 layer C', 'notes': 'Standard loader-provided'}, {'item': 'EXE-tree project module set minimum (Base/libcef confirmed; TenProxy etc. later)', 'address': 'C_RUNTIME', 'required_for_standalone': 'UNKNOWN', 'evidence_grade': 'CANDIDATE', 'source': 'CORE-009/010; EX-026/040', 'notes': 'Module set CONFIRMED; minimum UNKNOWN'}, {'item': 'Base.dll ordinal-1 boundary itself', 'address': 'Base RVA 0x1D6582C', 'required_for_standalone': 'UNKNOWN', 'evidence_grade': 'BOUNDARY', 'source': 'CORE-009/010', 'notes': 'Contract UNKNOWN; whether required at all if replaced is UNKNOWN'}, {'item': 'Internal dispatch table minimum', 'address': '0xCA81xx/0xCA84xx family', 'required_for_standalone': 'UNKNOWN', 'evidence_grade': 'CANDIDATE/UNKNOWN', 'source': 'CORE-010 GAP-P1-004; EX-045', 'notes': 'Indirect IAT/thunk slots with unbound API names'}, {'item': 'IIPS / IFS2 / CNIFS', 'address': 'BOOT_07', 'required_for_standalone': 'UNKNOWN', 'evidence_grade': 'BOUNDARY', 'source': 'EX-047/048/057/060', 'notes': 'Blocks progression past IIPS fatal, not the bootstrap entry itself'}, {'item': 'Tencent launcher components (WeGame/TCLS/Client.exe/tcls_core)', 'address': 'C_RUNTIME', 'required_for_standalone': 'NO', 'evidence_grade': 'NOT_REQUIRED_CONFIRMED', 'source': 'EX-026/046; CORE-010 audit', 'notes': 'Zero-Tencent native boot reached TenProxy/project DLL load stage'}, {'item': 'Network / STUN config', 'address': 'BOOT_06', 'required_for_standalone': 'UNKNOWN', 'evidence_grade': 'CANDIDATE', 'source': 'EX-043/044/045', 'notes': 'Endpoint selection confirmed; requirement unknown'}]

FIELDS_MODELS = ['model_id', 'name', 'external_dependency', 'controllability', 'evidence_strength', 'unknown_state_count', 'implementation_complexity', 'rollback_difficulty', 'pros', 'cons']
ROWS_MODELS = [{'model_id': 'MODEL_A', 'name': 'Minimal native bootstrap replacing ordinal-1, then chain head 0x77F580', 'external_dependency': 'NONE (in-process; Base ordinal-1 replaced)', 'controllability': 'HIGH (single controllable boundary at Entry)', 'evidence_strength': 'CANDIDATE', 'unknown_state_count': 'MEDIUM (ordinal-1 side effects, argv-provider binding)', 'implementation_complexity': 'HIGH (must reproduce argv/provider/gate sequence)', 'rollback_difficulty': 'LOW (no file modification; in-process only)', 'pros': 'All confirmed EXE-owned structures (argv globals, gate 0x849413B, token cluster, chain 0x77F580->...->0x6212C0) are plain .text with NO_TVM0_DEPENDENCY (EX-045); reuses known sufficient context (local tree + -q/-qa, EX-046)', 'cons': 'Chain upstream caller UNKNOWN (EX-045); CORE-011 proved chain does NOT execute post-ordinal-1; argv provider slot 0x00CA827C binder UNKNOWN; Base ordinal-1 pre-transfer side effects UNKNOWN'}, {'model_id': 'MODEL_B', 'name': 'Establish argv/global/dispatch minimum state, then direct entry into existing EXE native candidate', 'external_dependency': 'NONE (state written in-process)', 'controllability': 'HIGH', 'evidence_strength': 'CANDIDATE', 'unknown_state_count': 'HIGH (dispatch minimum, candidate entry conditions)', 'implementation_complexity': 'MEDIUM (state writes + direct transfer)', 'rollback_difficulty': 'LOW', 'pros': 'Avoids reproducing gate/argv logic; incrementally testable per candidate with known downstream call graph (EX-045); independent of argv-provider binding if globals written directly', 'cons': 'No candidate proven executable post-ordinal-1 (CORE-011 0/28); none proven as cold entry (L2 static only); 0x4FCEE0 internal state + indirect slots UNKNOWN; skipping 0x77F580 gate skips its other setup; Base ordinal-1 absence effect UNKNOWN'}]

FIELDS_GAPS = ['gap_id', 'description', 'evidence_grade', 'priority', 'source', 'notes']
ROWS_GAPS = [{'gap_id': 'GAP-P0-001', 'description': 'POST_BOUNDARY_CONTROL_TRANSFER: does EXE-image code execute at/after ordinal-1, and which module enters it', 'evidence_grade': 'UNKNOWN (CORE-011: NOT_OBSERVED for 7 historical candidates; does not prove no other EXE code runs)', 'priority': 'P0', 'source': 'CORE-010/011', 'notes': 'Primary blocker for standalone entry identification'}, {'gap_id': 'GAP-P0-002', 'description': 'BASE_ORDINAL1_BOUNDARY_CONTRACT: input/return/side-effect/termination semantics', 'evidence_grade': 'UNKNOWN', 'priority': 'P0', 'source': 'CORE-009/010', 'notes': '0/12 observed returns; never rewritten as nonreturn_confirmed'}, {'gap_id': 'GAP-P0-003', 'description': 'EXE_ENTRY_NATIVE_CONTINUATION: Entry-connected continuation', 'evidence_grade': 'NOT_FOUND (structural absence CONFIRMED; blocking UNKNOWN)', 'priority': 'P0', 'source': 'CORE-005/006/010', 'notes': '0x0E5DC696 is zero padding'}, {'gap_id': 'GAP-P0-004', 'description': 'OBSERVATION_ENVIRONMENT_DIVERGENCE: 0.67s (debugger) vs 7.7s (normal) timeline; Env B exits 0x4000001E before ordinal-1', 'evidence_grade': 'UNRESOLVED', 'priority': 'P0', 'source': 'CORE-010/011; EX-028', 'notes': 'Genuine execution-path difference, not instrumentation artifact'}, {'gap_id': 'GAP-P1-001', 'description': 'NATIVE_BOOTSTRAP_ENTRY_CONNECTION: caller of chain head 0x77F580', 'evidence_grade': 'UNKNOWN/CANDIDATE', 'priority': 'P1', 'source': 'CORE-010; EX-045', 'notes': 'Possible .tvm0 boundary above caller'}, {'gap_id': 'GAP-P1-002', 'description': 'IIPS_INITIALIZATION: first failing prerequisite; 0x8189FEC source', 'evidence_grade': 'UNKNOWN/CANDIDATE', 'priority': 'P1', 'source': 'CORE-010; EX-039/040/057', 'notes': 'PACKED_OR_VM_GENERATED; not equatable with IFS2 failure'}, {'gap_id': 'GAP-P1-003', 'description': 'ARGV_PROVIDER_SLOT: who binds 0x00CA827C, when it runs', 'evidence_grade': 'CANDIDATE', 'priority': 'P1', 'source': 'CORE-010; EX-032', 'notes': 'Slot holds 0x00A1517E at boundary entry 12/12'}, {'gap_id': 'GAP-P1-004', 'description': 'RUNTIME_DISPATCH_MINIMUM: minimum dispatch-table slot set', 'evidence_grade': 'CANDIDATE/UNKNOWN', 'priority': 'P1', 'source': 'CORE-010', 'notes': '0xCA81xx/0xCA84xx slots with unbound API names (EX-045)'}, {'gap_id': 'GAP-P1-005', 'description': '0x0849B500 static writer', 'evidence_grade': 'NOT_FOUND', 'priority': 'P1', 'source': 'CORE-010; EX-042', 'notes': 'Runtime-observed only'}, {'gap_id': 'GAP-P2-001', 'description': 'GAME_INIT / RENDERER_MAIN_LOOP entries', 'evidence_grade': 'UNKNOWN', 'priority': 'P2', 'source': 'CORE-010; EX-020', 'notes': 'No clean executable engine entry found'}, {'gap_id': 'GAP-P2-002', 'description': 'Project module loader edges (TenProxy/GameRpcs/TenRpcs/tcj/GDPLoader/GameDataPlatformServer)', 'evidence_grade': 'UNKNOWN', 'priority': 'P2', 'source': 'EX-026/027/040', 'notes': 'No caller edges captured'}, {'gap_id': 'GAP-P2-003', 'description': 'iips.dll loader/init/error caller (packed EXE/Base side)', 'evidence_grade': 'UNRESOLVED', 'priority': 'P2', 'source': 'EX-039/040', 'notes': 'No plain .text caller found'}, {'gap_id': 'GAP-P2-004', 'description': 'Base-internal node responsibilities (Base+0x2C96E/0x5F7000/0x5EB4E0/0x13A68/0x1D68B)', 'evidence_grade': 'UNKNOWN', 'priority': 'P2', 'source': 'EX-026/027', 'notes': 'Thread starts observed only; Base internals out of scope'}, {'gap_id': 'GAP-P2-005', 'description': 'Environment variables relevance', 'evidence_grade': 'UNKNOWN', 'priority': 'P2', 'source': 'CORE-010 layer A', 'notes': 'No ablation'}, {'gap_id': 'GAP-P2-006', 'description': 'EX-065 TCLS upstream protocol relevance to normal -q launch', 'evidence_grade': 'UNKNOWN (U11)', 'priority': 'P2', 'source': 'EX-065', 'notes': 'Named-object protocol keyed by game PID; whether exercised outside repair/pre-download unknown'}]

FIELDS_NEXT = ['experiment_id', 'purpose', 'single_variable', 'target_candidate', 'method', 'success_criterion', 'stop_condition', 'read_only', 'reversible', 'binary_modification', 'dll_modification', 'tencent_component_modification']
ROWS_NEXT = [{'experiment_id': 'E-012-01', 'purpose': 'Determine whether ANY EXE-image .text execution occurs after the ordinal-1 boundary (post-boundary EXE execution census), closing GAP-P0-001 and directly selecting between Model A and Model B entry targets', 'single_variable': 'EXE_IMAGE_CODE_EXECUTED_AFTER_ORDINAL1 in {OBSERVED, NOT_OBSERVED}', 'target_candidate': 'EXE .text section as a whole (execute coverage), with per-address attribution to 0x77F580/0x4FD9B0/0x4FCEE0/0x808650/0x7E98F0/0x6212C0/0x00561133/0x37FA70; ordinal-1 entry breakpoint retained as phase marker', 'method': 'Reuse CORE-009/CORE-011 observer (no file modification, no hooks, no Base internals): guard-page / execute-breakpoint coverage over EXE image .text range armed AFTER ordinal-1 entry breakpoint fires; record module/RVA/thread/timestamp per first hit; Environment A (CORE-009 reproduction) only, -q and no-arg cases', 'success_criterion': 'A first post-ordinal-1 EXE .text hit with RVA + thread recorded (OBSERVED) naming the actual post-boundary EXE entry; or 0 hits across both cases with ordinal-1 hit confirmed (NOT_OBSERVED), proving no EXE-image continuation exists in this environment', 'stop_condition': 'Stop at (a) first attributed EXE .text hit, or (b) process exit/timeout in both cases with ordinal-1 confirmed; stop before any Base-internal instrumentation; stop immediately on the known post-ordinal-1 0xC0000005 (RtlFreeHeap) exception', 'read_only': 'YES (observation only)', 'reversible': 'YES (process-memory breakpoints only)', 'binary_modification': 'NO', 'dll_modification': 'NO', 'tencent_component_modification': 'NO'}]

MD_TEXT = '# CODOL_STANDALONE_CORE_012\r\n# EXE-CORE-012 - Standalone Bootstrap Design\r\n\r\n## 0. Final Status\r\n\r\n```text\r\nSTANDALONE_BOOTSTRAP_ENTRY = CANDIDATE\r\nSTANDALONE_MINIMUM_STATE = PARTIAL\r\nBOUNDARY_REPLACEMENT_MODEL = DEFINED\r\nNEXT_EXPERIMENT = E-012-01\r\nFINAL_MARKER = STANDALONE_BOOTSTRAP_DESIGN_CANDIDATE\r\n```\r\n\r\n## 1. Fixed Goal\r\n\r\n> Make `codoMP_client_shipRetail.exe` establish a controllable standalone\r\n> bootstrap - independent of WeGame, TCLS, Client.exe or any other Tencent\r\n> launcher context - and eventually enter the game runtime that already\r\n> exists inside the EXE. This round does NOT try to restore the original\r\n> Tencent launch chain.\r\n\r\n## 2. Frozen Evidence Baseline\r\n\r\n```text\r\nEXE SHA256        : 36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537\r\nImageBase         : 0x00400000\r\nEntry RVA / VA    : 0x0E5DC690 / 0x0E9DC690\r\nEntry bytes       : FF 15 65 C6 9D 0E  (call dword ptr [0x0E9DC665])\r\nIAT slot          : RVA 0x0E5DC665 -> Base.dll ordinal 1 (0x80000001)\r\nReturn site       : RVA 0x0E5DC696 (zero padding, no fall-through)\r\nBase ordinal-1    : Base RVA 0x1D6582C\r\n```\r\n\r\nCORE-011 frozen verdict:\r\n\r\n```text\r\nEXE_IMAGE_EXECUTION_AFTER_BOUNDARY = NOT_OBSERVED   (7 historical candidates, 0/28 hits)\r\nENVIRONMENT_DEPENDENT              = NO\r\nSTANDALONE_BOOTSTRAP_DESIGN_READY  = YES\r\nHISTORICAL_BOOTSTRAP_CHAIN         = NOT_PROVEN_CURRENT_PATH\r\n```\r\n\r\n## 3. Phase 1 - EXE Runtime Entry Inventory\r\n\r\n### 3.A Entry-adjacent (CONFIRMED)\r\n\r\n```text\r\nEntry 0x0E5DC690  -> IAT[0x0E5DC665] -> Base.dll ordinal 1 (BOUNDARY)\r\n0x0E5DC696        -> zero padding; no native fall-through continuation\r\nordinal-1         -> 12/12 entries, 0/12 EXE return-site hits (CORE-009)\r\nboundary input    -> EAX/EDX/ESI/EDI/EFLAGS stable 12/12; semantic role UNKNOWN\r\nboundary state    -> 0x849413B=0, 0x849B501=0, argv_count=0, argv_array=0 (12/12)\r\n```\r\n\r\n### 3.B Confirmed EXE native structures\r\n\r\n| Address | Role | Evidence grade |\r\n|---|---|---|\r\n| `0x0849413B` | startup gate byte (`-q`); 1 write + 3 reads validated; runtime =1 during `-q` | CONFIRMED |\r\n| `0x0849B500` | `-qa` gate byte; 0 static operand sites; runtime-observed only | NOT_FOUND (static) |\r\n| `0x0849B501` | `-src=tgp` gate byte; 1 validated read, write NOT_FOUND | CONFIRMED read / NOT_FOUND write |\r\n| `0x08189FEC` | IIPS fatal status slot; 0 static producers; PACKED_OR_VM_GENERATED | NOT_FOUND |\r\n| `0x00CA827C` | argv provider dispatch slot; call site 0x00561133; runtime-bound | CANDIDATE |\r\n| `0x0196928C` | argv count global; write site 0x00561119 validated | CONFIRMED (shape) |\r\n| `0x01969290` | argv array global; sites 0x00239C2D/0x0056111E validated | CONFIRMED (shape) |\r\n| gate token cluster | `-qa` @ file 0x6C7F64, `-src=tgp` @ 0x6C7F68, `WIN_NO_TCLS` @ 0x6C7F80 (EXE-owned) | CONFIRMED |\r\n\r\n## 4. Phase 2 - Runtime Entry Candidates\r\n\r\nFull table: `exe_core012_entry_candidates.csv` (12 rows). Key facts:\r\n\r\n- All 7 historical candidates (`0x77F580`, `0x77F8B3`, `0x4FD9B0`, `0x4FCEE0`,\r\n  `0x808650`, `0x7E98F0`, `0x6212C0`) are CANDIDATE-grade: static L2 chain\r\n  CONFIRMED (EX-045, NO_TVM0_DEPENDENCY) but NOT_OBSERVED post-ordinal-1 (CORE-011).\r\n- Standalone-entry suitability: MAYBE for chain head/dispatchers\r\n  (`0x77F580`, `0x4FD9B0`, `0x4FCEE0`, `0x808650`, `0x7E98F0`); NO for leaf/mid sites\r\n  (`0x77F8B3`, `0x6212C0`, `0x00561133`, `0x37FA70`, `0x759F50`, engine anchors).\r\n- No candidate is CONFIRMED as a standalone entry. None depends on .tvm0 inside\r\n  the chain; upstream caller of `0x77F580` UNKNOWN (possible .tvm0 boundary).\r\n\r\n## 5. Phase 3 - Standalone Minimum State\r\n\r\nFull table: `exe_core012_minimum_state.csv` (16 rows). Summary:\r\n\r\n```text\r\nrequired_for_standalone = YES     : EXE image at ImageBase; command line (-q/-qa);\r\n                                    argv count/array globals; argv provider slot;\r\n                                    gate byte 0x0849413B=1; system CRT/DLLs\r\nrequired_for_standalone = NO      : Tencent launcher components (EX-026/046 proven)\r\nrequired_for_standalone = UNKNOWN : Base ordinal-1 itself; -qa/-src bytes; working\r\n                                    dir/tree; project module minimum; dispatch table\r\n                                    minimum; IIPS/IFS2/CNIFS; network/STUN config\r\n```\r\n\r\nAt the ordinal-1 boundary entry, argv globals and gate bytes are all still 0\r\n(12/12, CORE-009): a standalone bootstrap must establish argv + gate state\r\nitself; the observed pipeline establishes them only post-boundary.\r\n\r\n## 6. Phase 4 - Boundary Replacement Models\r\n\r\nFull table: `exe_core012_boundary_models.csv` (2 rows, facts only, no winner).\r\n\r\n### Model A - Minimal native bootstrap replacing ordinal-1\r\n\r\n```text\r\nEntry -> [replacement minimal native bootstrap: argv/provider/gate] -> 0x77F580 chain -> EXE runtime\r\n```\r\n\r\n- Pros: all confirmed structures are plain .text, NO_TVM0_DEPENDENCY (EX-045);\r\n  reuses known sufficient context (local tree + -q/-qa, EX-046); single\r\n  controllable boundary at Entry.\r\n- Cons: chain upstream caller UNKNOWN; CORE-011 proved the chain does NOT\r\n  execute post-ordinal-1; argv provider binder UNKNOWN; Base ordinal-1\r\n  pre-transfer side effects UNKNOWN.\r\n\r\n### Model B - Establish argv/global/dispatch minimum state, then direct entry\r\n\r\n```text\r\nEntry -> [establish argv globals + gate byte + dispatch minimum] -> 0x4FD9B0/0x4FCEE0 (or 0x77F580 pre-gated) -> EXE runtime\r\n```\r\n\r\n- Pros: avoids reproducing gate/argv logic; incrementally testable per\r\n  candidate; independent of argv-provider binding if globals written directly.\r\n- Cons: no candidate proven executable post-ordinal-1 (CORE-011 0/28); none\r\n  proven as cold entry (L2 static only); 0x4FCEE0 internal state and indirect\r\n  slots UNKNOWN; skipping 0x77F580 skips its other setup; Base ordinal-1\r\n  absence effect UNKNOWN.\r\n\r\nNo winner declared (spec section 10: factual comparison only).\r\n\r\n## 7. Gap List\r\n\r\nFull table: `exe_core012_gap_list.csv` (15 rows). P0 gaps:\r\n\r\n```text\r\nGAP-P0-001 POST_BOUNDARY_CONTROL_TRANSFER  UNKNOWN  (does ANY EXE code run after ordinal-1)\r\nGAP-P0-002 BASE_ORDINAL1_BOUNDARY_CONTRACT UNKNOWN  (input/return/side-effect/termination)\r\nGAP-P0-003 EXE_ENTRY_NATIVE_CONTINUATION   NOT_FOUND (structural absence; blocking UNKNOWN)\r\nGAP-P0-004 OBSERVATION_ENV_DIVERGENCE      UNRESOLVED (0.67s vs 7.7s; Env B pre-ordinal exit)\r\n```\r\n\r\n## 8. ONE Next Experiment\r\n\r\nFull record: `exe_core012_next_experiment.csv` (1 row).\r\n\r\n```text\r\nE-012-01  Post-boundary EXE .text execution census\r\nvariable  EXE_IMAGE_CODE_EXECUTED_AFTER_ORDINAL1 in {OBSERVED, NOT_OBSERVED}\r\nmethod    guard-page / execute-breakpoint coverage over the EXE image .text range,\r\n          armed AFTER the ordinal-1 entry breakpoint fires (CORE-009 observer reused),\r\n          Environment A only, -q and no-arg cases\r\nsuccess   first post-ordinal-1 EXE .text hit recorded with RVA+thread (OBSERVED),\r\n          or 0 hits in both cases with ordinal-1 confirmed (NOT_OBSERVED)\r\nstop      first attributed hit / exit / timeout; stop immediately on the known\r\n          post-ordinal-1 0xC0000005 (RtlFreeHeap) exception\r\nconstraints: read-only observation; reversible; no EXE/DLL/Tencent modification\r\n```\r\n\r\nPriority question answer:\r\n\r\n> Does a file-backed, EXE-proven native control-transfer target exist that can\r\n> serve as the experimental standalone bootstrap entry? **UNKNOWN** - static\r\n  candidates exist (MAYBE grade), but none is EXE-execution-proven in the\r\n  CORE-009 reproduction environment (CORE-011: 0/28). E-012-01 is the minimal\r\n  single-variable census that resolves this without manufacturing a candidate.\r\n\r\n## 9. Stop-condition evaluation\r\n\r\n```text\r\nSTOP-A (candidate with enough control-flow support) : NOT MET\r\n        (candidates exist but control-flow support is L2 static only;\r\n         execution linkage post-boundary is exactly what E-012-01 must test)\r\nSTOP-B (no implementable candidate)                 : NOT MET\r\n        (MAYBE candidates exist; scanning is not expanded further)\r\nSTOP-C (all viable candidates depend on .tvm0/Base/TenProxy/TCLS) : NOT MET\r\n        (chain itself is plain .text, NO_TVM0_DEPENDENCY, EX-045)\r\n=> verdict: continue with ONE experiment E-012-01 (minimal fixed-point dynamic validation)\r\n```\r\n\r\n## 10. Compliance Checklist\r\n\r\n| Spec requirement | Status |\r\n|---|---|\r\n| Only EXE analyzed; existing CORE-001..011 artifacts reused | PASS |\r\n| No Base.dll/.tvm0/TenProxy/TCLS/WeGame internals | PASS |\r\n| No Procmon/Sandboxie; no whole-EXE bootstrap rescan | PASS |\r\n| 7 dead historical candidates not re-investigated (used as frozen inputs only) | PASS |\r\n| No EXE/DLL modification; no .tvm0 patch; no Tencent hook | PASS |\r\n| 0x849B500 old-report error NOT re-introduced (kept NOT_FOUND) | PASS |\r\n| required_for_standalone column on every state row | PASS |\r\n| Two boundary models, no winner | PASS |\r\n| Exactly ONE next experiment (E-012-01), single-variable, read-only, reversible | PASS |\r\n| UNKNOWN kept UNKNOWN; no fake CONFIRMED | PASS |\r\n| generator/artifact/hash/row-count validation in generator | PASS |\r\n\r\n## 11. Artifacts\r\n\r\n```text\r\nCODOL_STANDALONE_CORE_012_BOOTSTRAP_DESIGN.md   (this file)\r\nexe_core012_entry_candidates.csv                (12 rows)\r\nexe_core012_minimum_state.csv                   (16 rows)\r\nexe_core012_boundary_models.csv                 (2 rows)\r\nexe_core012_gap_list.csv                        (15 rows)\r\nexe_core012_next_experiment.csv                 (1 row)\r\ncore012_bootstrap_design.py                     (generator, re-run to reproduce)\r\n```\r\n\r\n## 12. Final Status (repeat, per spec)\r\n\r\n```text\r\nSTANDALONE_BOOTSTRAP_ENTRY = CANDIDATE\r\nSTANDALONE_MINIMUM_STATE = PARTIAL\r\nBOUNDARY_REPLACEMENT_MODEL = DEFINED\r\nNEXT_EXPERIMENT = E-012-01\r\nFINAL_MARKER = STANDALONE_BOOTSTRAP_DESIGN_CANDIDATE\r\n```\r\n\r\n> Prefer one honest UNKNOWN over one fabricated CONFIRMED.\r\n'


def validate_entry_candidates(rows: list[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    ids = [row["candidate_id"] for row in rows]
    if len(ids) != len(set(ids)):
        errors.append("entry candidate ids are not unique")
    rvas = {row["rva"] for row in rows}
    for rva in HISTORICAL_CHAIN_RVAS:
        if rva not in rvas:
            errors.append(f"historical chain RVA missing from inventory: {rva}")
    yes = [row["candidate_id"] for row in rows if row["standalone_suitable"] == "YES"]
    if yes:
        errors.append(
            "no EXE-proven standalone entry exists: standalone_suitable=YES is forbidden while "
            f"STANDALONE_BOOTSTRAP_ENTRY=CANDIDATE, found {yes}"
        )
    maybe = sorted(row["candidate_id"] for row in rows if row["standalone_suitable"] == "MAYBE")
    if maybe != ["C012-4FCEE0", "C012-4FD9B0", "C012-77F580", "C012-7E98F0", "C012-808650"]:
        errors.append(f"MAYBE standalone-entry set drifted: {maybe}")
    for row in rows:
        if row["standalone_suitable"] not in ("YES", "NO", "MAYBE"):
            errors.append(f"{row['candidate_id']}: invalid standalone_suitable {row['standalone_suitable']}")
        if row["required_for_standalone"] not in ("YES", "NO", "UNKNOWN"):
            errors.append(f"{row['candidate_id']}: invalid required_for_standalone {row['required_for_standalone']}")
        if not grade_ok(row["evidence_grade"]):
            errors.append(f"{row['candidate_id']}: invalid evidence_grade {row['evidence_grade']}")
        if row["post_ordinal1_observed"].startswith("OBSERVED"):
            errors.append(f"{row['candidate_id']}: post-ordinal-1 OBSERVED contradicts CORE-011 0/28")
        if row["standalone_suitable"] == "MAYBE" and not row["evidence_grade"].startswith("CANDIDATE"):
            errors.append(f"{row['candidate_id']}: MAYBE standalone entry requires CANDIDATE grade")
        if row["evidence_grade"].startswith("CONFIRMED") and row["standalone_suitable"] == "MAYBE":
            errors.append(f"{row['candidate_id']}: CONFIRMED-grade row must not stay MAYBE")
        if row["tvm0_dependency"].startswith("YES"):
            errors.append(f"{row['candidate_id']}: in-chain tvm0 dependency must stay NO/UNKNOWN")
    return errors


def validate_minimum_state(rows: list[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    for row in rows:
        if row["required_for_standalone"] not in ("YES", "NO", "UNKNOWN"):
            errors.append(f"state {row['item']}: invalid required_for_standalone {row['required_for_standalone']}")
        if not grade_ok(row["evidence_grade"]):
            errors.append(f"state {row['item']}: invalid evidence_grade {row['evidence_grade']}")
    gate = next((r for r in rows if r["address"] == "0x0849413B"), None)
    if gate is None or gate["required_for_standalone"] != "YES" or not gate["evidence_grade"].startswith("CONFIRMED"):
        errors.append("startup gate byte 0x0849413B must stay YES/CONFIRMED")
    qa = next((r for r in rows if "0x0849B500" in r["address"]), None)
    if qa is None or "NOT_FOUND" not in qa["evidence_grade"]:
        errors.append("0x0849B500 must keep NOT_FOUND (old-report error not re-introduced)")
    tencent = next((r for r in rows if r["item"].startswith("Tencent launcher")), None)
    if (
        tencent is None
        or tencent["required_for_standalone"] != "NO"
        or "NOT_REQUIRED_CONFIRMED" not in tencent["evidence_grade"]
    ):
        errors.append("Tencent launcher components must stay NO/NOT_REQUIRED_CONFIRMED")
    return errors


def validate_boundary_models(rows: list[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    ids = sorted(row["model_id"] for row in rows)
    if ids != ["MODEL_A", "MODEL_B"]:
        errors.append(f"boundary models must be exactly MODEL_A and MODEL_B, found {ids}")
    for row in rows:
        for field in (
            "external_dependency", "controllability", "evidence_strength",
            "unknown_state_count", "implementation_complexity", "rollback_difficulty",
            "pros", "cons",
        ):
            if not row[field]:
                errors.append(f"{row['model_id']}: empty field {field}")
        joined = (row["name"] + row["pros"] + row["cons"]).lower()
        if "winner" in joined or "chosen" in joined:
            errors.append(f"{row['model_id']}: model comparison must stay factual (no winner)")
    return errors


def validate_gaps(rows: list[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    ids = [row["gap_id"] for row in rows]
    if len(ids) != len(set(ids)):
        errors.append("gap ids are not unique")
    for row in rows:
        if not row["gap_id"].startswith("GAP-"):
            errors.append(f"gap id not in GAP-* form: {row['gap_id']}")
        if row["priority"] not in ("P0", "P1", "P2", "P3"):
            errors.append(f"{row['gap_id']}: invalid priority {row['priority']}")
        if not grade_ok(row["evidence_grade"]):
            errors.append(f"{row['gap_id']}: invalid evidence_grade {row['evidence_grade']}")
        if row["priority"] == "P0" and row["evidence_grade"].startswith("CONFIRMED"):
            errors.append(
                f"{row['gap_id']}: no P0 gap may be CONFIRMED while the post-boundary "
                "control transfer stays UNKNOWN"
            )
    p0 = sorted(row["gap_id"] for row in rows if row["priority"] == "P0")
    if p0 != ["GAP-P0-001", "GAP-P0-002", "GAP-P0-003", "GAP-P0-004"]:
        errors.append(f"P0 gap set drifted: {p0}")
    qa = next((r for r in rows if "0x0849B500" in r["description"]), None)
    if qa is None or not qa["evidence_grade"].startswith("NOT_FOUND"):
        errors.append("GAP for the 0x0849B500 static writer must stay NOT_FOUND")
    return errors


def validate_next_experiment(rows: list[dict[str, str]], embedded: list[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    if len(rows) != 1:
        errors.append("next experiment table must contain exactly one row")
        return errors
    row = rows[0]
    if row["experiment_id"] != "E-012-01":
        errors.append(f"next experiment id drifted: {row['experiment_id']}")
    for field in ("read_only", "reversible"):
        if not row[field].startswith("YES"):
            errors.append(f"E-012-01 must stay {field}=YES")
    for field in ("binary_modification", "dll_modification", "tencent_component_modification"):
        if row[field] != "NO":
            errors.append(f"E-012-01 must stay {field}=NO")
    if "guard-page" not in row["method"]:
        errors.append("E-012-01 method must stay a guard-page/execute-breakpoint census")
    if "OBSERVED" not in row["success_criterion"] or "NOT_OBSERVED" not in row["success_criterion"]:
        errors.append("E-012-01 success criterion must keep the OBSERVED/NOT_OBSERVED dichotomy")
    # the design record must not be silently retargeted to another experiment
    design = {r["experiment_id"] for r in embedded}
    if {row["experiment_id"]} != design:
        errors.append(f"next experiment retargeted: on-disk {row['experiment_id']} vs design {sorted(design)}")
    return errors


def validate_report(text: str) -> list[str]:
    errors: list[str] = []
    for line in FINAL_STATUS:
        if line not in text:
            errors.append(f"report missing final status line: {line}")
    for block in text.splitlines():
        if "0x0849B500" in block and "CONFIRMED" in block and "NOT_FOUND" not in block:
            errors.append(f"report line upgrades 0x0849B500 to CONFIRMED: {block.strip()}")
    if "ORDINAL1_NON_RETURN = CONFIRMED" in text or "nonreturn_confirmed" in text:
        errors.append("report must not rewrite 0/12 observed returns as confirmed non-return")
    return errors


def check_row_counts() -> list[str]:
    errors: list[str] = []
    for key, name in CSV_NAMES.items():
        rows = read_csv(name)
        if len(rows) != EXPECTED_ROWS[key]:
            errors.append(f"{name}: expected {EXPECTED_ROWS[key]} rows, found {len(rows)}")
    return errors


def main() -> int:
    st = verify_static()
    design = embedded_rows()
    disk = load_artifacts()

    errors: list[str] = []
    errors += check_static(st)
    errors += check_inputs()
    errors += check_core011()
    errors += artifact_agreement(design, disk)
    errors += data_input_errors()
    errors += validate_entry_candidates(disk["ENTRY"])
    errors += validate_minimum_state(disk["STATE"])
    errors += validate_boundary_models(disk["MODELS"])
    errors += validate_gaps(disk["GAPS"])
    errors += validate_next_experiment(disk["NEXT"], design["NEXT"])
    errors += validate_report(MD_OUT.read_text(encoding="utf-8") if MD_OUT.is_file() else "")

    print("=" * 78)
    print("CODOL_STANDALONE_CORE_012 - Standalone Bootstrap Design")
    print("=" * 78)
    print(f"sample SHA-256 match      : {st['exe_sha256'] == EXE_SHA256}")
    print(f"Entry bytes re-decode     : {st['entry_bytes']} (match {st['entry_bytes'] == ENTRY_BYTES})")
    print(f"IAT slot                  : 0x{IAT_SLOT_VA:X} = 0x{st['iat_slot_value']:08X} (Base ordinal 1)")
    print(f"EXE import descriptors    : {len(st['import_names'])} ({' / '.join(st['import_names'])})")
    print(f"base relocation directory : size {st['reloc_dir_size']}")
    print(f"Entry zero-padding span   : {st['entry_fallthrough_zero_span']} bytes")
    print(f"gate tokens present       : {st['gate_tokens']}")
    print(f"entry candidates          : {len(disk['ENTRY'])} rows"
          f" ({len(HISTORICAL_CHAIN_RVAS)} historical chain RVAs)")
    print(f"minimum state             : {len(disk['STATE'])} rows")
    print(f"boundary models           : {len(disk['MODELS'])} (facts only, no winner)")
    print(f"gap list                  : {len(disk['GAPS'])} rows"
          f"  P0 {sum(1 for r in disk['GAPS'] if r['priority'] == 'P0')}"
          f"  P1 {sum(1 for r in disk['GAPS'] if r['priority'] == 'P1')}"
          f"  P2 {sum(1 for r in disk['GAPS'] if r['priority'] == 'P2')}")
    print(f"next experiment           : {disk['NEXT'][0]['experiment_id'] if disk['NEXT'] else 'MISSING'}"
          f" (single variable)")
    print("-" * 78)
    for line in FINAL_STATUS:
        print(line)
    print("-" * 78)

    if errors:
        print(f"VALIDATION: FAIL ({len(errors)} problem(s)) - NOT REWRITING ARTIFACTS")
        for err in errors:
            print(f"  - {err}")
        return 1

    # Only a fully consistent design is allowed to (re)produce the artifacts.
    written = [
        write_csv(CSV_NAMES["ENTRY"], FIELDS_ENTRY, ROWS_ENTRY),
        write_csv(CSV_NAMES["STATE"], FIELDS_STATE, ROWS_STATE),
        write_csv(CSV_NAMES["MODELS"], FIELDS_MODELS, ROWS_MODELS),
        write_csv(CSV_NAMES["GAPS"], FIELDS_GAPS, ROWS_GAPS),
        write_csv(CSV_NAMES["NEXT"], FIELDS_NEXT, ROWS_NEXT),
    ]
    with MD_OUT.open("w", encoding="utf-8", newline="") as fh:
        fh.write(MD_TEXT)
    written.append(MD_OUT)

    post = check_row_counts() + artifact_agreement(design, load_artifacts())
    if post:
        errors += post
        print(f"VALIDATION: FAIL ({len(errors)} problem(s)) - write did not converge")
        for err in errors:
            print(f"  - {err}")
        return 1

    print("VALIDATION: PASS (CORE-012 design rules enforced)")
    print("-" * 78)
    for path in written:
        digest = hashlib.sha256(path.read_bytes()).hexdigest().upper()
        print(f"WROTE {path.name}  sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
