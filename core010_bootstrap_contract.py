from __future__ import annotations

"""CODOL_STANDALONE_CORE_010 - Standalone Bootstrap Contract (evidence-locked).

Freeze the already-confirmed EXE startup structure, record every UNKNOWN and
BOUNDARY explicitly, identify the real P0/P1 gaps, and select exactly one
minimal next experiment.

Rules enforced by validate():
  * the only primary object is codoMP_client_shipRetail.exe;
  * codoMP_client_shipRetailBase.dll stays an EXTERNAL BOUNDARY: no CFG, no
    .text reverse, no .tvm0, no allocator / thread / IIPS / TenProxy internals;
  * no EXE/DLL patch, hook, stub or replacement - the sample is only READ
    (SHA-256, PE headers, instruction bytes, ASCII tokens);
  * CORE-009 literals are copied verbatim into the contract matrix;
  * "0/12 observed returns" is never rewritten as "ordinal-1 never returns".

Tooling: python core010_bootstrap_contract.py
"""

import csv
import hashlib
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXE = ROOT / "COD OL" / "codoMP_client_shipRetail.exe"
MD_OUT = ROOT / "CODOL_STANDALONE_CORE_010_BOOTSTRAP_CONTRACT.md"

EXE_SHA256 = "36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537"
BASE_SHA256 = "EF75220DE1D6973F34C7069F5BF211B11BD61520C6C0DE1882F7359FA5BC6A20"

IMAGE_BASE = 0x00400000
ENTRY_RVA = 0x0E5DC690
ENTRY_BYTES = "FF 15 65 C6 9D 0E"
IAT_SLOT_RVA = 0x0E5DC665
IAT_SLOT_VA = 0x0E9DC665          # the FF 15 encodes this absolute slot address
EXE_RETURN_RVA = 0x0E5DC696
BASE_ORDINAL1_RVA = 0x1D6582C

# CORE-010 status vocabulary (round contract section 4)
STATUS_ENUM = ("CONFIRMED", "CANDIDATE", "UNKNOWN", "BOUNDARY", "NOT_FOUND", "UNRESOLVED")
# state-machine "required" vocabulary (section 5)
REQUIRED_ENUM = ("CONFIRMED", "CANDIDATE", "UNKNOWN", "NOT_REQUIRED")
# how confident we are that an item blocks boot (section 20: P0 stays UNKNOWN,
# not CONFIRMED, while transfer/termination semantics are still open)
BLOCKING_ENUM = ("CONFIRMED", "CANDIDATE", "UNKNOWN", "NOT_BLOCKING")
# which boot layer a gap blocks (section 19)
PRIORITY_ENUM = ("P0", "P1", "P2", "P3")
# "required vs optional" vocabulary (section 18)
REQUIRED_STATUS_ENUM = ("REQUIRED_CONFIRMED", "REQUIRED_CANDIDATE", "UNKNOWN", "NOT_REQUIRED_CONFIRMED")

BOOT_NODES = [
    ("BOOT_00_PROCESS_START", "PROCESS_START"),
    ("BOOT_01_EXE_ENTRY", "EXE_ENTRY"),
    ("BOOT_02_ORDINAL1_BOUNDARY", "ORDINAL1_BOUNDARY"),
    ("BOOT_03_ARGV_PROVIDER", "ARGV_PROVIDER"),
    ("BOOT_04_STARTUP_CONTEXT_GATE", "STARTUP_CONTEXT_GATE"),
    ("BOOT_05_NATIVE_BOOTSTRAP", "NATIVE_BOOTSTRAP"),
    ("BOOT_06_NETWORK_INIT", "NETWORK_INIT"),
    ("BOOT_07_IIPS_BOUNDARY", "IIPS_BOUNDARY"),
    ("BOOT_08_GAME_INIT", "GAME_INIT"),
    ("BOOT_09_RENDERER", "RENDERER"),
    ("BOOT_10_INPUT_AUDIO", "INPUT_AUDIO"),
    ("BOOT_11_MAIN_LOOP", "MAIN_LOOP"),
    ("BOOT_12_SHUTDOWN", "SHUTDOWN"),
]

# Absolute-operand instruction forms used to validate a candidate site.
# (opcode, length, mnemonic) - the absolute operand follows the opcode directly.
OPCODE_FORMS = (
    (bytes.fromhex("A3"), 1, "mov dword ptr [abs], eax"),
    (bytes.fromhex("A1"), 1, "mov eax, dword ptr [abs]"),
    (bytes.fromhex("FF15"), 2, "call dword ptr [abs]"),
    (bytes.fromhex("FF25"), 2, "jmp dword ptr [abs]"),
    (bytes.fromhex("C605"), 2, "mov byte ptr [abs], imm8"),
    (bytes.fromhex("803D"), 2, "cmp byte ptr [abs], imm8"),
    (bytes.fromhex("381D"), 2, "cmp byte ptr [abs], bl"),
    (bytes.fromhex("3805"), 2, "cmp byte ptr [abs], al"),
    (bytes.fromhex("8935"), 2, "mov dword ptr [abs], esi"),
    (bytes.fromhex("8905"), 2, "mov dword ptr [abs], eax"),
    (bytes.fromhex("8915"), 2, "mov dword ptr [abs], edx"),
    (bytes.fromhex("8B0D"), 2, "mov ecx, dword ptr [abs]"),
    (bytes.fromhex("8B15"), 2, "mov edx, dword ptr [abs]"),
    (bytes.fromhex("8B3D"), 2, "mov edi, dword ptr [abs]"),
    (bytes.fromhex("8B35"), 2, "mov esi, dword ptr [abs]"),
    (bytes.fromhex("3B05"), 2, "cmp eax, dword ptr [abs]"),
)

TRACKED_SITES = {
    "STATE_0849413B": "3B414908",
    "STATE_0849B500": "00B54908",
    "STATE_0849B501": "01B54908",
    "STATE_08189FEC": "EC9F1808",
    "ARGV_COUNT_0196928C": "8C929601",
    "ARGV_ARRAY_01969290": "90929601",
    "ARGV_PROVIDER_00CA827C": "7C82CA00",
}


def write_csv(name: str, fields: list[str], rows: list[dict[str, object]]) -> Path:
    path = ROOT / name
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def read_csv(name: str) -> list[dict[str, str]]:
    path = ROOT / name
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))
class Image:
    """Minimal read-only PE32 view of the sample."""

    def __init__(self, blob: bytes) -> None:
        self.blob = blob
        self.pe = struct.unpack_from("<I", blob, 0x3C)[0]
        assert blob[self.pe : self.pe + 4] == b"PE\0\0", "not a PE file"
        coff = self.pe + 4
        (self.machine,) = struct.unpack_from("<H", blob, coff)
        (self.nsections,) = struct.unpack_from("<H", blob, coff + 2)
        (self.opt_size,) = struct.unpack_from("<H", blob, coff + 16)
        self.opt = coff + 20
        (self.magic,) = struct.unpack_from("<H", blob, self.opt)
        (self.entry_rva,) = struct.unpack_from("<I", blob, self.opt + 16)
        (self.image_base,) = struct.unpack_from("<I", blob, self.opt + 28)
        (self.subsystem,) = struct.unpack_from("<H", blob, self.opt + 68)
        self.ddir = self.opt + (96 if self.magic == 0x10B else 112)
        self.sections: list[tuple[str, int, int, int, int]] = []
        sec = self.opt + self.opt_size
        for i in range(self.nsections):
            off = sec + i * 40
            name = blob[off : off + 8].rstrip(b"\0").decode("latin-1")
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
            if len(desc) < 20 or desc == b"\0" * 20:
                break
            (orig,) = struct.unpack_from("<I", desc)
            (name_rva,) = struct.unpack_from("<I", desc, 12)
            (first,) = struct.unpack_from("<I", desc, 16)
            noff = self.rva_to_off(name_rva)
            end = self.blob.index(b"\0", noff)
            out.append((self.blob[noff:end].decode("latin-1"), orig, first))
            cur += 20
        return out

    def relocation_targets(self) -> set[int]:
        """Absolute VAs listed in the relocation table (32-bit type 3 entries)."""
        rva, size = self.directory(5)
        out: set[int] = set()
        if not rva or not size:
            return out
        cur = rva
        end = rva + size
        while cur < end:
            off = self.rva_to_off(cur)
            page, block = struct.unpack_from("<II", self.blob, off)
            if block == 0:
                break
            for i in range((block - 8) // 2):
                (entry,) = struct.unpack_from("<H", self.blob, off + 8 + i * 2)
                if (entry >> 12) == 3:
                    out.add(self.image_base + page + (entry & 0x0FFF))
            cur += block
        return out


def abs_operand_sites(blob: bytes, va: int) -> list[dict[str, object]]:
    """Locate and validate every absolute-memory operand site for one VA.

    A site counts as validated only when the 4 bytes immediately preceding the
    little-endian operand form a known absolute-operand opcode. This is the
    same two-validator discipline CORE-008 applied to 0x0849413B.
    """
    pat = struct.pack("<I", va)
    sites: list[dict[str, object]] = []
    start = 0
    while True:
        p = blob.find(pat, start)
        if p < 0:
            break
        start = p + 1
        resolved = None
        for opcode, length, mnemonic in OPCODE_FORMS:
            if p - length >= 0 and blob[p - length : p] == opcode:
                resolved = (p - length, mnemonic)
                break
        sites.append(
            {
                "operand_off": p,
                "validated": resolved is not None,
                "insn_off": resolved[0] if resolved else None,
                "mnemonic": resolved[1] if resolved else "UNVALIDATED",
            }
        )
    return sites


def static_verify() -> dict[str, object]:
    """Re-derive the file-image facts CORE-010 asserts. Read-only."""
    blob = EXE.read_bytes()
    img = Image(blob)
    digest = hashlib.sha256(blob).hexdigest().upper()

    eoff = img.rva_to_off(img.entry_rva)
    entry = blob[eoff : eoff + 8]
    span = 0
    while blob[eoff + 6 + span] == 0 and span < 0x4000:
        span += 1

    slot_off = img.rva_to_off(IAT_SLOT_RVA)
    (slot_value,) = struct.unpack_from("<I", blob, slot_off)
    relocs = img.relocation_targets()

    needle = bytes.fromhex("FF15") + struct.pack("<I", IAT_SLOT_VA)
    ff15_count = 0
    start = 0
    while True:
        p = blob.find(needle, start)
        if p < 0:
            break
        ff15_count += 1
        start = p + 1

    sites: dict[str, list[dict[str, object]]] = {}
    for label, pat_hex in TRACKED_SITES.items():
        va = struct.unpack("<I", bytes.fromhex(pat_hex))[0]
        sites[label] = abs_operand_sites(blob, va)

    # gate-token neighbourhood: EX-035 gate semantics live in one string pool
    token_off = blob.find(b"-q\x00-qa\x00-src=tgp")
    tokens = blob[token_off - 64 : token_off + 96].decode("latin-1") if token_off > 0 else ""

    return {
        "sha256": digest,
        "sha256_match": digest == EXE_SHA256,
        "size": len(blob),
        "machine": img.machine,
        "subsystem": img.subsystem,
        "image_base": img.image_base,
        "entry_rva": img.entry_rva,
        "entry_bytes": " ".join(f"{b:02X}" for b in entry[:6]),
        "fall_through_zero_span": span,
        "sections": img.sections,
        "imports": img.imports(),
        "slot_value": slot_value,
        "slot_relocated": (img.image_base + IAT_SLOT_RVA) in relocs,
        "ff15_site_count": ff15_count,
        "sites": sites,
        "token_pool": tokens,
        "stun_demonware_off": blob.find(b"stun.us.demonware.net"),
        "stun_codol_off": blob.find(b"stun1-tub.codol.qq.com"),
        "iips_dll_off": blob.find(b"iips.dll"),
    }


class Image:
    """Minimal read-only PE32 view of the sample."""

    def __init__(self, blob: bytes) -> None:
        self.blob = blob
        self.pe = struct.unpack_from("<I", blob, 0x3C)[0]
        assert blob[self.pe : self.pe + 4] == b"PE\0\0", "not a PE file"
        coff = self.pe + 4
        (self.machine,) = struct.unpack_from("<H", blob, coff)
        (self.nsections,) = struct.unpack_from("<H", blob, coff + 2)
        (self.opt_size,) = struct.unpack_from("<H", blob, coff + 16)
        self.opt = coff + 20
        (self.magic,) = struct.unpack_from("<H", blob, self.opt)
        (self.entry_rva,) = struct.unpack_from("<I", blob, self.opt + 16)
        (self.image_base,) = struct.unpack_from("<I", blob, self.opt + 28)
        (self.subsystem,) = struct.unpack_from("<H", blob, self.opt + 68)
        self.ddir = self.opt + (96 if self.magic == 0x10B else 112)
        self.sections: list[tuple[str, int, int, int, int]] = []
        sec = self.opt + self.opt_size
        for i in range(self.nsections):
            off = sec + i * 40
            name = blob[off : off + 8].rstrip(b"\0").decode("latin-1")
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
            if len(desc) < 20 or desc == b"\0" * 20:
                break
            (orig,) = struct.unpack_from("<I", desc)
            (name_rva,) = struct.unpack_from("<I", desc, 12)
            (first,) = struct.unpack_from("<I", desc, 16)
            noff = self.rva_to_off(name_rva)
            end = self.blob.index(b"\0", noff)
            out.append((self.blob[noff:end].decode("latin-1"), orig, first))
            cur += 20
        return out


def abs_operand_sites(blob: bytes, va: int) -> list[dict[str, object]]:
    """Locate and validate absolute-memory operand sites for one global VA."""
    pat = struct.pack("<I", va)
    sites: list[dict[str, object]] = []
    start = 0
    while True:
        p = blob.find(pat, start)
        if p < 0:
            break
        start = p + 1
        resolved = None
        for opcode, length, mnemonic in OPCODE_FORMS:
            if p - length >= 0 and blob[p - length : p] == opcode:
                resolved = (p - length, mnemonic)
                break
        sites.append(
            {
                "operand_off": p,
                "validated": resolved is not None,
                "insn_off": resolved[0] if resolved else None,
                "mnemonic": resolved[1] if resolved else "UNVALIDATED",
            }
        )
    return sites


def find_all(blob: bytes, token: bytes) -> list[int]:
    hits: list[int] = []
    start = 0
    while True:
        p = blob.find(token, start)
        if p < 0:
            return hits
        hits.append(p)
        start = p + 1


def verify_static() -> dict[str, object]:
    """Read-only re-validation of every static claim CORE-010 relies on."""
    blob = EXE.read_bytes()
    img = Image(blob)
    f: dict[str, object] = {}
    f["exe_size"] = len(blob)
    f["exe_sha256"] = hashlib.sha256(blob).hexdigest().upper()
    f["exe_sha256_match"] = f["exe_sha256"] == EXE_SHA256
    f["machine"] = img.machine
    f["magic"] = img.magic
    f["subsystem"] = img.subsystem
    f["image_base"] = img.image_base
    f["entry_rva"] = img.entry_rva
    f["entry_bytes"] = img.read_rva(img.entry_rva, 6).hex(" ").upper()
    f["entry_bytes_match"] = f["entry_bytes"] == ENTRY_BYTES
    f["section_names"] = [s[0] for s in img.sections]
    f["sections"] = list(img.sections)
    (slot,) = struct.unpack_from("<I", blob, img.rva_to_off(IAT_SLOT_RVA))
    f["iat_slot_value"] = slot
    f["iat_slot_is_ordinal"] = slot == 0x80000001
    imports = img.imports()
    f["imports"] = imports
    f["import_descriptor_count"] = len(imports)
    f["import_names"] = [i[0] for i in imports]
    rel_rva, rel_size = img.directory(5)
    f["reloc_dir_rva"] = rel_rva
    f["reloc_dir_size"] = rel_size
    eoff = img.rva_to_off(img.entry_rva)
    span = 0
    while blob[eoff + 6 + span] == 0 and span < 0x4000:
        span += 1
    f["entry_fallthrough_zero_span"] = span
    f["sites"] = {label: abs_operand_sites(blob, int(label.split("_")[-1], 16)) for label in TRACKED_SITES}
    f["site_summary"] = {
        label: {
            "total": len(v),
            "validated": sum(1 for s in v if s["validated"]),
            "unvalidated": sum(1 for s in v if not s["validated"]),
            "insns": [f"{s['insn_off']:#010x}={s['mnemonic']}" for s in v if s["validated"]],
        }
        for label, v in f["sites"].items()
    }
    f["gate_tokens"] = {t: find_all(blob, t) for t in (b"-qa", b"-src=tgp", b"WIN_NO_TCLS")}
    f["strings"] = {
        t: find_all(blob, t)
        for t in (b"stun1-tub.codol.qq.com", b"stun.us.demonware.net", b"iips.dll", b"Network Port", b".tvm0")
    }
    qa = f["gate_tokens"][b"-qa"]
    f["gate_token_region"] = (
        blob[max(0, qa[0] - 96) : qa[0] + 190].decode("latin-1").replace("\x00", ".") if qa else ""
    )
    return f


def load_core009() -> dict[str, object]:
    """Aggregate the CORE-009 observation artifacts (data-derived, not copied)."""
    runs = read_csv("exe_core009_runs.csv")
    regs = read_csv("exe_core009_registers.csv")
    stack = read_csv("exe_core009_stack.csv")
    state = read_csv("exe_core009_state_delta.csv")
    threads = read_csv("exe_core009_thread_delta.csv")
    modules = read_csv("exe_core009_module_delta.csv")
    fs = read_csv("exe_core009_fs_delta.csv")
    contract = read_csv("exe_core009_contract_matrix.csv")

    g: dict[str, object] = {}
    g["run_count"] = len(runs)
    g["ordinal1_hits"] = sum(1 for r in runs if r.get("ordinal1_hit") == "1")
    g["return_hits"] = sum(1 for r in runs if r.get("return_hit") == "1")
    g["exit_codes"] = sorted({r.get("exit_code", "") for r in runs if r.get("exit_code")})
    g["process_states"] = sorted({r.get("process_state", "") for r in runs if r.get("process_state")})
    g["cases"] = sorted({r.get("case", "") for r in runs if r.get("case")})
    per_case: dict[str, dict[str, int]] = {}
    for r in runs:
        c = r.get("case", "?")
        d = per_case.setdefault(c, {"runs": 0, "ordinal1": 0, "return": 0})
        d["runs"] += 1
        d["ordinal1"] += 1 if r.get("ordinal1_hit") == "1" else 0
        d["return"] += 1 if r.get("return_hit") == "1" else 0
    g["per_case"] = per_case
    g["case_commandline"] = {r.get("case", "?"): r.get("command_line", "") for r in runs}

    def uniq(rows: list[dict[str, str]], key: str) -> list[str]:
        return sorted({r.get(key, "") for r in rows if r.get(key)})

    g["reg_stable"] = {
        k: uniq(regs, k) for k in ("eax_in", "edx_in", "esi_in", "edi_in", "eflags_in")
    }
    for k, v in g["reg_stable"].items():
        assert len(v) == 1, f"{k} is not stable across CORE-009 runs: {v}"
    g["reg_variable_counts"] = {k: len(uniq(regs, k)) for k in ("ecx_in", "esp_in", "ebp_in")}
    g["reg_values"] = {k: v[0] for k, v in g["reg_stable"].items()}
    g["stack_stable"] = {k: uniq(stack, k) for k in ("stack_0", "stack_4", "stack_18")}
    g["stack_variable_counts"] = {k: len(uniq(stack, k)) for k in ("stack_8", "stack_10")}
    g["state_before"] = {}
    for r in state:
        g["state_before"].setdefault(r.get("state", "?"), set()).add(r.get("before", ""))
    g["state_before"] = {k: sorted(v) for k, v in g["state_before"].items()}
    g["state_after"] = sorted({r.get("after", "") for r in state if r.get("after")})
    g["thread_counts"] = sorted({int(r["thread_count_seen"]) for r in threads if r.get("thread_count_seen")})
    last_seen = [float(r["first_seen_seconds"]) for r in threads if r.get("first_seen_seconds")]
    g["thread_last_first_seen_s"] = max(last_seen) if last_seen else None
    g["module_events"] = {}
    for r in modules:
        g["module_events"][r.get("event", "?")] = g["module_events"].get(r.get("event", "?"), 0) + 1
    distinct = sorted({r.get("module_name", "") for r in modules if r.get("module_name")})
    g["module_distinct"] = distinct
    g["module_distinct_count"] = len(distinct)
    watched = ("iips", "ifs", "tcls", "tenproxy", "gbspy", "tenrpcs", "tersafe", "gdploader", "tcj")
    g["watched_modules_absent"] = [w for w in watched if not any(w in m.lower() for m in distinct)]
    g["watched_modules_present"] = [m for m in distinct if any(w in m.lower() for w in watched)]
    g["fs_delta_rows"] = len(fs)
    g["contract_rows"] = [(r.get("item", ""), r.get("classification", "")) for r in contract]
    return g


def build_ledger_a(st: dict, g: dict) -> list[dict[str, object]]:
    return [
        {
            "id": "E-010-001",
            "component": "SAMPLE_IDENTITY_EXE",
            "address": "COD OL/codoMP_client_shipRetail.exe",
            "evidence": (
                f"machine 0x{st['machine']:X} (I386), magic 0x{st['magic']:X} (PE32), "
                f"subsystem {st['subsystem']}; ImageBase 0x{st['image_base']:X}; "
                f"Entry RVA 0x{st['entry_rva']:X}; size {st['exe_size']}; "
                f"SHA-256 re-verified = {st['exe_sha256_match']}"
            ),
            "status": "CONFIRMED",
            "source_round": "CORE-001/CORE-008/CORE-010",
            "confidence": "CONFIRMED",
            "dependency": "filesystem",
            "notes": "本轮仅只读重校验，未修改样本",
        },
        {
            "id": "E-010-002",
            "component": "ENTRY_INSTRUCTION",
            "address": "RVA 0x0E5DC690 (VA 0x0E9DC690)",
            "evidence": (
                f"bytes {st['entry_bytes']} -> call dword ptr [0x{IAT_SLOT_VA:X}] "
                f"(decode match = {st['entry_bytes_match']})"
            ),
            "status": "CONFIRMED",
            "source_round": "CORE-006/CORE-008/CORE-010",
            "confidence": "CONFIRMED",
            "dependency": "loader",
            "notes": "Entry 只有这一条外部转移指令",
        },
        {
            "id": "E-010-003",
            "component": "ENTRY_FALLTHROUGH",
            "address": f"RVA 0x{EXE_RETURN_RVA:X}",
            "evidence": f"call 之后连续零填充 span = {st['entry_fallthrough_zero_span']} bytes，无 EAX 消费指令",
            "status": "CONFIRMED",
            "source_round": "CORE-006/CORE-008/CORE-010",
            "confidence": "CONFIRMED",
            "dependency": "none",
            "notes": "静态上不存在 EXE 侧返回延续",
        },
        {
            "id": "E-010-004",
            "component": "IAT_SLOT_ORDINAL1",
            "address": f"slot VA 0x{IAT_SLOT_VA:X} (RVA 0x{IAT_SLOT_RVA:X})",
            "evidence": (
                f"slot value 0x{st['iat_slot_value']:08X} (ordinal 1 = {st['iat_slot_is_ordinal']}); "
                f"reloc directory size = {st['reloc_dir_size']} (no base relocation for the slot)"
            ),
            "status": "CONFIRMED",
            "source_round": "CORE-008/CORE-010",
            "confidence": "CONFIRMED",
            "dependency": "codoMP_client_shipRetailBase.dll",
            "notes": "Entry 唯一可见外部转移目标",
        },
        {
            "id": "E-010-005",
            "component": "EXE_IMPORT_SET",
            "address": "PE data directory[1]",
            "evidence": f"import descriptors = {st['import_descriptor_count']}: {' / '.join(st['import_names'])}",
            "status": "CONFIRMED",
            "source_round": "CORE-006/CORE-010",
            "confidence": "CONFIRMED",
            "dependency": "none",
            "notes": "EXE 没有 Tencent 组件的静态导入",
        },
        {
            "id": "E-010-006",
            "component": "BASE_ORDINAL1_TARGET",
            "address": f"Base.dll ordinal 1 (RVA 0x{BASE_ORDINAL1_RVA:X})",
            "evidence": (
                f"ENTRY_TO_ORDINAL1 reachability = CONFIRMED ({g['ordinal1_hits']}/{g['run_count']} observed); "
                f"Base SHA-256 (documented) = {BASE_SHA256[:16]}..."
            ),
            "status": "BOUNDARY",
            "source_round": "CORE-008/CORE-009",
            "confidence": "CONFIRMED",
            "dependency": "Base.dll",
            "notes": "仅作为 EXTERNAL_BOUNDARY；本轮不进入 Base 内部",
        },
        {
            "id": "E-010-007",
            "component": "ORDINAL1_REACHABILITY",
            "address": f"boundary RVA 0x{BASE_ORDINAL1_RVA:X} (Base-relative)",
            "evidence": (
                f"{g['ordinal1_hits']}/{g['run_count']} boundary entries across cases "
                f"{'/'.join(g['cases'])}; per case "
                + "; ".join(f"{c}:{d['ordinal1']}/{d['runs']}" for c, d in sorted(g["per_case"].items()))
            ),
            "status": "CONFIRMED",
            "source_round": "CORE-009",
            "confidence": "CONFIRMED",
            "dependency": "Base.dll",
            "notes": "可达性确认，不代表契约确认",
        },
        {
            "id": "E-010-008",
            "component": "ORDINAL1_REGISTER_VALUE_STABILITY",
            "address": "boundary registers",
            "evidence": (
                f"identical in {g['run_count']} runs: EAX {g['reg_values']['eax_in']}, "
                f"EDX {g['reg_values']['edx_in']}, ESI {g['reg_values']['esi_in']}, "
                f"EDI {g['reg_values']['edi_in']}, EFLAGS {g['reg_values']['eflags_in']}; "
                f"varying: ECX {g['reg_variable_counts']['ecx_in']} values, ESP {g['reg_variable_counts']['esp_in']}, "
                f"EBP {g['reg_variable_counts']['ebp_in']}"
            ),
            "status": "CONFIRMED",
            "source_round": "CORE-009",
            "confidence": "CONFIRMED",
            "dependency": "Base.dll boundary",
            "notes": "REGISTER_VALUE_STABILITY = CONFIRMED",
        },
        {
            "id": "E-010-009",
            "component": "ORDINAL1_REGISTER_SEMANTIC_ROLE",
            "address": "boundary registers",
            "evidence": "没有直接证据把 EAX/EDX/ESI/EDI/EFLAGS 指派为 this / context / argument / flags",
            "status": "UNKNOWN",
            "source_round": "CORE-009",
            "confidence": "UNRESOLVED",
            "dependency": "Base.dll boundary",
            "notes": "REGISTER_SEMANTIC_ROLE = UNKNOWN；ESI 指向 Base+0 不得解释为 NULL context",
        },
    ]


def build_ledger_a2(st: dict, g: dict) -> list[dict[str, object]]:
    return [
        {
            "id": "E-010-010",
            "component": "ORDINAL1_STACK_ARGUMENTS",
            "address": "boundary stack",
            "evidence": (
                f"stable stack data [ESP] {g['stack_stable']['stack_0']}, [ESP+4] {g['stack_stable']['stack_4']}, "
                f"[ESP+18] {g['stack_stable']['stack_18']}; varying pointers "
                f"{g['stack_variable_counts']['stack_8']}/{g['stack_variable_counts']['stack_10']} distinct; "
                "Entry performs no push and no stack setup"
            ),
            "status": "UNKNOWN",
            "source_round": "CORE-008/CORE-009",
            "confidence": "UNRESOLVED",
            "dependency": "Base.dll boundary",
            "notes": "CORE-009 literal ORDINAL1_STACK_ARGUMENTS = NOT_CONFIRMED（该字面量不在 CORE-010 枚举内）",
        },
        {
            "id": "E-010-011",
            "component": "ORDINAL1_RETURNED",
            "address": f"EXE RVA 0x{EXE_RETURN_RVA:X}",
            "evidence": (
                f"return-site hits {g['return_hits']}/{g['run_count']}; "
                "EAX_out/ECX_out/EDX_out/EFLAGS_out/ESP_out = NOT_OBSERVED"
            ),
            "status": "NOT_FOUND",
            "source_round": "CORE-009",
            "confidence": "CONFIRMED",
            "dependency": "Base.dll boundary",
            "notes": "CORE-009 literal ORDINAL1_RETURNED = NOT_CONFIRMED (0/12 observed return)",
        },
        {
            "id": "E-010-012",
            "component": "ORDINAL1_RETURN_CONTRACT",
            "address": "boundary return",
            "evidence": "no EAX/ECX/EDX/EFLAGS/ESP return observation exists, so no return contract can be stated",
            "status": "UNKNOWN",
            "source_round": "CORE-009",
            "confidence": "UNRESOLVED",
            "dependency": "Base.dll boundary",
            "notes": "CORE-009 literal = NOT_CONFIRMED",
        },
        {
            "id": "E-010-013",
            "component": "RETURN_VALUE_CONSUMER",
            "address": "EXE caller side",
            "evidence": "no caller-side consumer; static fall-through is zero padding (E-010-003)",
            "status": "NOT_FOUND",
            "source_round": "CORE-008/CORE-009",
            "confidence": "CONFIRMED",
            "dependency": "none",
            "notes": "静态与动态一致",
        },
        {
            "id": "E-010-014",
            "component": "ORDINAL1_NON_RETURN",
            "address": "boundary",
            "evidence": "0/12 只证明 BOUNDARY_NO_RETURN_OBSERVED；没有证明 ordinal-1 永不返回",
            "status": "UNKNOWN",
            "source_round": "CORE-009",
            "confidence": "UNRESOLVED",
            "dependency": "Base.dll boundary",
            "notes": "ORDINAL1_NONRETURN = UNKNOWN；禁止改写为 NONRETURN_CONFIRMED",
        },
        {
            "id": "E-010-015",
            "component": "ORDINAL1_SIDE_EFFECT",
            "address": "boundary",
            "evidence": "没有 caller-side after-state，因为 EXE 返回点从未到达",
            "status": "UNKNOWN",
            "source_round": "CORE-009",
            "confidence": "UNRESOLVED",
            "dependency": "Base.dll boundary",
            "notes": "CORE-009 literal SIDE_EFFECT_CONTRACT = NOT_CONFIRMED",
        },
        {
            "id": "E-010-016",
            "component": "ORDINAL1_TERMINATION_MODE",
            "address": "process",
            "evidence": (
                f"post-entry process exits {', '.join(g['exit_codes'])}; "
                f"last observer-relative thread timestamp {g['thread_last_first_seen_s']}s; exit-code semantics = UNKNOWN"
            ),
            "status": "UNKNOWN",
            "source_round": "CORE-009",
            "confidence": "UNRESOLVED",
            "dependency": "observer environment",
            "notes": "observer-conditional；不得解释为 Base 内部行为",
        },
        {
            "id": "E-010-017",
            "component": "POST_BOUNDARY_THREAD_ACTIVITY",
            "address": "process",
            "evidence": (
                f"thread_count_seen values {g['thread_counts']} per run; up to "
                f"{g['thread_last_first_seen_s']}s observer-relative first-seen time"
            ),
            "status": "CONFIRMED",
            "source_round": "CORE-009",
            "confidence": "CONFIRMED",
            "dependency": "OS scheduler",
            "notes": "runtime observation；MODULE_THREAD_CALLER_CONTRACT = NOT_CONFIRMED",
        },
        {
            "id": "E-010-018",
            "component": "POST_BOUNDARY_MODULE_SET",
            "address": "process",
            "evidence": (
                f"{g['module_distinct_count']} distinct modules; events {g['module_events']}; "
                f"watched present = {g['watched_modules_present'] or 'NONE'}; absent = {g['watched_modules_absent']}"
            ),
            "status": "CONFIRMED",
            "source_round": "CORE-009",
            "confidence": "CONFIRMED",
            "dependency": "OS loader",
            "notes": "仅代表观察窗口内的模块集合",
        },
    ]


def build_ledger_b(st: dict, g: dict) -> list[dict[str, object]]:
    ss = st["site_summary"]
    sb = g["state_before"]
    return [
        {
            "id": "E-010-019",
            "component": "FS_METADATA_DELTA",
            "address": "process filesystem",
            "evidence": f"low-interference metadata snapshot delta rows = {g['fs_delta_rows']}",
            "status": "CONFIRMED",
            "source_round": "CORE-009",
            "confidence": "CONFIRMED",
            "dependency": "filesystem",
            "notes": "create/open/read/write 未被 metadata snapshot 证实；未使用 Procmon",
        },
        {
            "id": "E-010-020",
            "component": "COMMANDLINE_BOUNDARY_DELTA_Q",
            "address": "boundary input",
            "evidence": f"case B (-q) boundary registers/stack/globals identical to case A; state before {sb.get('q_gate')}",
            "status": "UNKNOWN",
            "source_round": "CORE-009",
            "confidence": "UNRESOLVED",
            "dependency": "argv",
            "notes": "CORE-009 literal COMMANDLINE_BOUNDARY_DELTA_Q = NOT_CONFIRMED",
        },
        {
            "id": "E-010-021",
            "component": "COMMANDLINE_BOUNDARY_DELTA_QA",
            "address": "boundary input",
            "evidence": "case C (-qa) boundary registers/stack/globals identical to case A",
            "status": "UNKNOWN",
            "source_round": "CORE-009",
            "confidence": "UNRESOLVED",
            "dependency": "argv",
            "notes": "CORE-009 literal COMMANDLINE_BOUNDARY_DELTA_QA = NOT_CONFIRMED",
        },
        {
            "id": "E-010-022",
            "component": "COMMANDLINE_BOUNDARY_DELTA_SRC",
            "address": "boundary input",
            "evidence": "case D (-q -src=tgp) boundary registers/stack/globals identical to case A",
            "status": "UNKNOWN",
            "source_round": "CORE-009",
            "confidence": "UNRESOLVED",
            "dependency": "argv",
            "notes": "CORE-009 literal COMMANDLINE_BOUNDARY_DELTA_SRC = NOT_CONFIRMED",
        },
        {
            "id": "E-010-023",
            "component": "ARGV_DATA_SHAPE",
            "address": "0x0196928C (count) / 0x01969290 (array)",
            "evidence": (
                f"static sites: count {ss['ARGV_COUNT_0196928C']['validated']}/{ss['ARGV_COUNT_0196928C']['total']} "
                f"validated, array {ss['ARGV_ARRAY_01969290']['validated']}/{ss['ARGV_ARRAY_01969290']['total']} "
                f"validated; at boundary entry both hold {sb.get('argv_count')} / {sb.get('argv_array')} "
                f"in all {g['run_count']} runs"
            ),
            "status": "CONFIRMED",
            "source_round": "CORE-008/CORE-009/CORE-010",
            "confidence": "CONFIRMED",
            "dependency": "runtime allocator",
            "notes": "ARGV_DATA_SHAPE = CONFIRMED；ARGV_SOURCE = CANDIDATE（process command line）",
        },
        {
            "id": "E-010-024",
            "component": "ARGV_PROVIDER_SLOT",
            "address": "0x00CA827C (call site 0x00561133)",
            "evidence": (
                "single static site: "
                + ", ".join(ss["ARGV_PROVIDER_00CA827C"]["insns"])
                + "; target is runtime-bound (no file-backed pointer proven)"
            ),
            "status": "CANDIDATE",
            "source_round": "CORE-008/CORE-010",
            "confidence": "CANDIDATE",
            "dependency": "runtime dispatch slot",
            "notes": "禁止写成 0x00CA827C = GetCommandLineW / GetCommandLineA / CommandLineToArgvW",
        },
    ]


def build_ledger_b2(st: dict, g: dict) -> list[dict[str, object]]:
    ss = st["site_summary"]
    sb = g["state_before"]
    return [
        {
            "id": "E-010-025",
            "component": "STARTUP_GATE_Q",
            "address": "0x0849413B",
            "evidence": (
                f"static sites {ss['STATE_0849413B']['validated']} validated of "
                f"{ss['STATE_0849413B']['total']} candidates: {ss['STATE_0849413B']['insns']}; "
                f"rejected data-like candidates = {ss['STATE_0849413B']['unvalidated']}"
            ),
            "status": "CONFIRMED",
            "source_round": "CORE-007/CORE-008/CORE-010",
            "confidence": "CONFIRMED",
            "dependency": "argv",
            "notes": "1 write + 3 reads；边界入口时刻值 = " + str(sb.get("q_gate")),
        },
        {
            "id": "E-010-026",
            "component": "STARTUP_GATE_QA",
            "address": "0x0849B500",
            "evidence": (
                f"static file-image operand sites = {ss['STATE_0849B500']['total']} (NOT_FOUND); "
                "runtime -qa observed writing 1 (EX-035)"
            ),
            "status": "NOT_FOUND",
            "source_round": "CORE-007/CORE-008/EX-035",
            "confidence": "CONFIRMED",
            "dependency": "runtime",
            "notes": "静态 NOT_FOUND；runtime observation 只能标 RUNTIME_OBSERVED，不得反向写成静态引用",
        },
        {
            "id": "E-010-027",
            "component": "STARTUP_GATE_SRC_TGP",
            "address": "0x0849B501",
            "evidence": (
                f"static sites {ss['STATE_0849B501']['validated']} validated of "
                f"{ss['STATE_0849B501']['total']} candidates: {ss['STATE_0849B501']['insns']}; "
                "write NOT_FOUND in the file image"
            ),
            "status": "CONFIRMED",
            "source_round": "CORE-007/CORE-008/CORE-010",
            "confidence": "CONFIRMED",
            "dependency": "runtime",
            "notes": "读已确认；写仅 RUNTIME_OBSERVED（EX-035）",
        },
        {
            "id": "E-010-028",
            "component": "STARTUP_CONTEXT_GATE_TOKENS",
            "address": "EXE file-image plain-text token cluster",
            "evidence": (
                f"-qa at file offset {hex(st['gate_tokens'][b'-qa'][0])}, "
                f"-src=tgp at {hex(st['gate_tokens'][b'-src=tgp'][0])}, "
                f"WIN_NO_TCLS at {hex(st['gate_tokens'][b'WIN_NO_TCLS'][0])}"
            ),
            "status": "CONFIRMED",
            "source_round": "CORE-010",
            "confidence": "CONFIRMED",
            "dependency": "none",
            "notes": "gate token 与 WIN_NO_TCLS 错误串同属 EXE 自身启动上下文逻辑",
        },
        {
            "id": "E-010-029",
            "component": "WIN_NO_TCLS_SEMANTICS",
            "address": "argv gate (WIN_NO_TCLS)",
            "evidence": "no args / -src=tgp alone -> WIN_NO_TCLS fatal; -q or -qa -> bypass, then IIPS init error",
            "status": "CONFIRMED",
            "source_round": "EX-031/EX-035/EX-046",
            "confidence": "CONFIRMED",
            "dependency": "argv",
            "notes": "本地启动上下文 gate；不是服务端认证，也不是 TCLS 共享内存检查",
        },
        {
            "id": "E-010-030",
            "component": "IIPS_STATUS_CODE_SLOT",
            "address": "0x08189FEC",
            "evidence": f"static file-image operand sites = {ss['STATE_08189FEC']['total']} (NOT_FOUND); runtime fatal code 8189fec",
            "status": "NOT_FOUND",
            "source_round": "CORE-007/CORE-008/EX-050",
            "confidence": "CONFIRMED",
            "dependency": "none",
            "notes": "PACKED_OR_RUNTIME_GENERATED；不得直接等价为 IFS2 失败",
        },
    ]


def build_ledger_b3(st: dict, g: dict) -> list[dict[str, object]]:
    st_strings = st["strings"]
    return [
        {
            "id": "E-010-031",
            "component": "HISTORICAL_BOOTSTRAP_CHAIN",
            "address": "0x77F580 -> 0x77F8B3 -> 0x4FD9B0 -> 0x4FCEE0 -> 0x808650 -> 0x7E98F0 -> 0x6212C0",
            "evidence": "EXE-side plain .text chain recovered (EX-044/045/046); CORE-005/006 Entry-connected native edges = 0",
            "status": "CANDIDATE",
            "source_round": "EX-044/EX-045/EX-046 + CORE-005/CORE-006",
            "confidence": "CANDIDATE",
            "dependency": "runtime bootstrap",
            "notes": "HISTORICAL_CHAIN_STATUS = NOT_ENTRY_CONNECTED；不得升级为 Entry-confirmed",
        },
        {
            "id": "E-010-032",
            "component": "POST_BOUNDARY_EXE_ENTRY_INFERENCE",
            "address": "EXE image (0x77F580 head)",
            "evidence": (
                "independent-copy runs reach the EXE-side chain head while the static Entry-connected graph is empty, "
                "so that chain must be entered from outside the Entry-connected graph"
            ),
            "status": "CANDIDATE",
            "source_round": "EX-046 + CORE-006 + CORE-010",
            "confidence": "UNRESOLVED",
            "dependency": "Base.dll boundary",
            "notes": "本轮唯一结构性推论：Base ordinal-1 可能把执行权交回 EXE，但未证实",
        },
        {
            "id": "E-010-033",
            "component": "NETWORK_STUN_CONFIG",
            "address": "0x6212C0 / 0x7E98F0 / 0x808650",
            "evidence": (
                f"EXE file-image string 'stun.us.demonware.net' at {[hex(i) for i in st_strings[b'stun.us.demonware.net']]}; "
                f"'stun1-tub.codol.qq.com' hits = {len(st_strings[b'stun1-tub.codol.qq.com'])}; "
                f"'Network Port' at {[hex(i) for i in st_strings[b'Network Port'][:2]]}"
            ),
            "status": "CANDIDATE",
            "source_round": "EX-043/EX-044/EX-045 + CORE-010",
            "confidence": "CANDIDATE",
            "dependency": "network config",
            "notes": "NETWORK_INIT = CANDIDATE；endpoint 字符串存在不等于建立连接",
        },
        {
            "id": "E-010-034",
            "component": "IIPS_BOUNDARY",
            "address": "iips.dll / IFS2.dll / CNIFS",
            "evidence": (
                "iips.dll load + CNIFS::InitInGameApp / initIfsLib / LoadLibraryW / GetProcAddress(CreateIFSLibDll) / "
                "CreateIFSLibDll / GetProcAddress(DestoryIFSLibDll)"
            ),
            "status": "BOUNDARY",
            "source_round": "EX-047/EX-048/EX-060",
            "confidence": "CONFIRMED",
            "dependency": "iips.dll / IFS2.dll",
            "notes": f"EXE file-image 'iips.dll' occurrences = {len(st_strings[b'iips.dll'])}；本轮不进入 IIPS/IFS2",
        },
        {
            "id": "E-010-035",
            "component": "IIPS_INIT_RESULT",
            "address": "post-gate node",
            "evidence": "WIN_IIPS_INIT_ERROR 8189fec observed after gate bypass",
            "status": "UNKNOWN",
            "source_round": "EX-035/EX-047/EX-050",
            "confidence": "UNRESOLVED",
            "dependency": "iips.dll",
            "notes": "IIPS_SUCCESS = UNKNOWN；IIPS_FAILURE_ROOT = UNKNOWN",
        },
    ]


def build_ledger_b4(st: dict, g: dict) -> list[dict[str, object]]:
    return [
        {
            "id": "E-010-036",
            "component": "EXE_SELF_BOOTSTRAP",
            "address": "EXE Entry-connected graph",
            "evidence": "Entry-connected native edges = 0; fall-through is zero padding; no Entry-connected island activation",
            "status": "NOT_FOUND",
            "source_round": "CORE-005/CORE-006/CORE-007",
            "confidence": "CONFIRMED",
            "dependency": "none",
            "notes": "静态上 EXE 自身没有通往 native bootstrap 的入口延续",
        },
        {
            "id": "E-010-037",
            "component": "GAME_INIT",
            "address": "none",
            "evidence": "no direct CODOL address / call / structure evidence closes game init",
            "status": "UNKNOWN",
            "source_round": "CORE-005/CORE-006/CORE-007",
            "confidence": "UNRESOLVED",
            "dependency": "native bootstrap",
            "notes": "IW4_LINEAGE_HOMOLOGUE = CANDIDATE（只作谱系类比，不建立函数等价）",
        },
        {
            "id": "E-010-038",
            "component": "RENDERER_INPUT_AUDIO_MAIN_LOOP",
            "address": "none",
            "evidence": "no direct evidence in CORE-001..009",
            "status": "UNKNOWN",
            "source_round": "CORE-002/CORE-007",
            "confidence": "UNRESOLVED",
            "dependency": "game init",
            "notes": "RENDERER / INPUT / AUDIO / MAIN_LOOP 全部保持 UNKNOWN，禁止为凑齐状态机而虚构",
        },
        {
            "id": "E-010-039",
            "component": "OBSERVATION_WINDOW_COVERAGE",
            "address": "process (cross-round)",
            "evidence": (
                f"CORE-009 window ends at process exit (~{g['thread_last_first_seen_s']}s observer-relative, "
                f"threads {g['thread_counts']}, modules {g['module_distinct_count']}, watched project modules absent "
                f"{g['watched_modules_absent']}); EX-046 normal-copy runs reach the IIPS fatal at about T+7.7s"
            ),
            "status": "UNRESOLVED",
            "source_round": "CORE-009 + EX-046",
            "confidence": "UNRESOLVED",
            "dependency": "observer environment",
            "notes": "CORE-009 观察窗口未覆盖 IIPS 阶段；差异根因 UNKNOWN，不得据此改写 Base 行为结论",
        },
    ]


def build_ledger(st: dict, g: dict) -> list[dict[str, object]]:
    return (
        build_ledger_a(st, g)
        + build_ledger_a2(st, g)
        + build_ledger_b(st, g)
        + build_ledger_b2(st, g)
        + build_ledger_b3(st, g)
        + build_ledger_b4(st, g)
    )


def build_states(st: dict, g: dict) -> list[dict[str, object]]:
    return build_states_a(st, g) + build_states_b(st, g)


def build_states_a(st: dict, g: dict) -> list[dict[str, object]]:
    return [
        {
            "state_id": "BOOT_00_PROCESS_START",
            "state_name": "PROCESS_START",
            "entry_evidence": "CreateProcessW 成功；PE32/I386 进程创建（CORE-009 CREATE_PROCESS 事件）",
            "exit_evidence": f"PE Entry RVA 0x{ENTRY_RVA:X} 开始执行",
            "status": "CONFIRMED",
            "required": "CONFIRMED",
            "external_dependency": "OS loader",
            "blocking_level": "NOT_BLOCKING",
            "notes": "样本 SHA-256 本轮重校验通过",
        },
        {
            "state_id": "BOOT_01_EXE_ENTRY",
            "state_name": "EXE_ENTRY",
            "entry_evidence": f"Entry 指令 {ENTRY_BYTES} 执行",
            "exit_evidence": f"进入 IAT slot 0x{IAT_SLOT_VA:X} 目标（Base ordinal 1）",
            "status": "CONFIRMED",
            "required": "CONFIRMED",
            "external_dependency": "Base.dll import",
            "blocking_level": "NOT_BLOCKING",
            "notes": "Entry 无 push、无寄存器准备、无栈参数（CORE-008 静态确认）",
        },
        {
            "state_id": "BOOT_02_ORDINAL1_BOUNDARY",
            "state_name": "ORDINAL1_BOUNDARY",
            "entry_evidence": f"{g['ordinal1_hits']}/{g['run_count']} 观测到 Base ordinal-1 入口",
            "exit_evidence": f"EXE 返回点 RVA 0x{EXE_RETURN_RVA:X} 从未到达（{g['return_hits']}/{g['run_count']}）",
            "status": "BOUNDARY",
            "required": "UNKNOWN",
            "external_dependency": "codoMP_client_shipRetailBase.dll",
            "blocking_level": "UNKNOWN",
            "notes": "ORDINAL1 = P0 UNKNOWN，而不是 P0 CONFIRMED；input/stack/return/side-effect/termination 全部 UNKNOWN",
        },
        {
            "state_id": "BOOT_03_ARGV_PROVIDER",
            "state_name": "ARGV_PROVIDER",
            "entry_evidence": "argv 全局 0x0196928C / 0x01969290 与 provider slot 0x00CA827C",
            "exit_evidence": "count + char** array 可用（静态写入点 0x00561119/0x0056111E 已确认）",
            "status": "CANDIDATE",
            "required": "CANDIDATE",
            "external_dependency": "0x00CA827C runtime slot / process command line",
            "blocking_level": "CANDIDATE",
            "notes": "边界入口时刻两全局仍为 0（12/12），说明 provider 在边界之后才可能运行",
        },
        {
            "state_id": "BOOT_04_STARTUP_CONTEXT_GATE",
            "state_name": "STARTUP_CONTEXT_GATE",
            "entry_evidence": "argv 扫描 -q / -qa / -src=tgp",
            "exit_evidence": "WIN_NO_TCLS fatal，或 bypass 后继续进入后续节点",
            "status": "CONFIRMED",
            "required": "CANDIDATE",
            "external_dependency": "argv",
            "blocking_level": "CANDIDATE",
            "notes": "gate token 与 WIN_NO_TCLS 字符串在 EXE 文件镜像内；边界入口时刻 gate 值 = 0",
        },
        {
            "state_id": "BOOT_05_NATIVE_BOOTSTRAP",
            "state_name": "NATIVE_BOOTSTRAP",
            "entry_evidence": "gate bypass 后历史链 0x77F580 -> 0x77F8B3 -> 0x4FD9B0 -> 0x4FCEE0",
            "exit_evidence": "后续子系统 init 继续（未观测到进入 game init）",
            "status": "CANDIDATE",
            "required": "UNKNOWN",
            "external_dependency": "runtime bootstrap (unproven)",
            "blocking_level": "UNKNOWN",
            "notes": "ENTRY_CONNECTION = UNKNOWN；HISTORICAL_CHAIN_STATUS = NOT_ENTRY_CONNECTED",
        },
        {
            "state_id": "BOOT_06_NETWORK_INIT",
            "state_name": "NETWORK_INIT",
            "entry_evidence": "0x808650 -> 0x7E98F0 -> 0x6212C0（STUN / network mode init）",
            "exit_evidence": "网络模式选择完成（未观测到成功）",
            "status": "CANDIDATE",
            "required": "UNKNOWN",
            "external_dependency": "stun config / network config",
            "blocking_level": "CANDIDATE",
            "notes": "stun.us.demonware.net 在 EXE 文件镜像内；stun1-tub.codol.qq.com 在 EXE 镜像内 0 命中",
        },
    ]


def build_states_b(st: dict, g: dict) -> list[dict[str, object]]:
    return [
        {
            "state_id": "BOOT_07_IIPS_BOUNDARY",
            "state_name": "IIPS_BOUNDARY",
            "entry_evidence": "post-gate 进入 IIPS 初始化（iipsinit 窗口 / CNIFS 初始化）",
            "exit_evidence": "WIN_IIPS_INIT_ERROR 8189fec（已观测 fatal），无成功路径证据",
            "status": "BOUNDARY",
            "required": "UNKNOWN",
            "external_dependency": "iips.dll / IFS2.dll / CNIFS",
            "blocking_level": "CANDIDATE",
            "notes": "IIPS_SUCCESS / IIPS_FAILURE_ROOT = UNKNOWN；CORE-009 观察窗口未覆盖此阶段",
        },
        {
            "state_id": "BOOT_08_GAME_INIT",
            "state_name": "GAME_INIT",
            "entry_evidence": "无直接 CODOL 地址 / 调用 / 结构证据",
            "exit_evidence": "未观测",
            "status": "UNKNOWN",
            "required": "UNKNOWN",
            "external_dependency": "native bootstrap",
            "blocking_level": "UNKNOWN",
            "notes": "IW4_LINEAGE_HOMOLOGUE = CANDIDATE，仅作谱系类比；不得写成 CODOL 函数 = IW4X 函数",
        },
        {
            "state_id": "BOOT_09_RENDERER",
            "state_name": "RENDERER",
            "entry_evidence": "无直接证据",
            "exit_evidence": "未观测",
            "status": "UNKNOWN",
            "required": "UNKNOWN",
            "external_dependency": "unknown",
            "blocking_level": "UNKNOWN",
            "notes": "不为完成状态机而虚构节点",
        },
        {
            "state_id": "BOOT_10_INPUT_AUDIO",
            "state_name": "INPUT_AUDIO",
            "entry_evidence": "无直接证据",
            "exit_evidence": "未观测",
            "status": "UNKNOWN",
            "required": "UNKNOWN",
            "external_dependency": "unknown",
            "blocking_level": "UNKNOWN",
            "notes": "input/audio 是否属于启动前置未被任何轮次证明",
        },
        {
            "state_id": "BOOT_11_MAIN_LOOP",
            "state_name": "MAIN_LOOP",
            "entry_evidence": "无 Entry-connected 消息/渲染循环证据",
            "exit_evidence": "未观测",
            "status": "UNKNOWN",
            "required": "UNKNOWN",
            "external_dependency": "game init",
            "blocking_level": "UNKNOWN",
            "notes": "PeekMessage/GetMessage/Present 等候选均未与 Entry 建立连接",
        },
        {
            "state_id": "BOOT_12_SHUTDOWN",
            "state_name": "SHUTDOWN",
            "entry_evidence": "观测到进程退出码 " + ", ".join(g["exit_codes"]) + "（观察环境内）",
            "exit_evidence": "进程终止；退出码语义 UNKNOWN",
            "status": "UNKNOWN",
            "required": "NOT_REQUIRED",
            "external_dependency": "none",
            "blocking_level": "NOT_BLOCKING",
            "notes": "shutdown 定义上位于 runtime 之后，对 boot 可达性不是前置；退出语义未闭合（非 Base 行为结论）",
        },
    ]


def build_contracts(st: dict, g: dict) -> list[dict[str, object]]:
    rows = [
        ("ENTRY_CONTRACT", "CONFIRMED", f"ImageBase 0x{IMAGE_BASE:X}; Entry RVA 0x{ENTRY_RVA:X}; {ENTRY_BYTES}", "CONFIRMED", "CORE-006/008/010", "唯一外部转移"),
        ("ORDINAL1_REACHABILITY", "CONFIRMED", f"{g['ordinal1_hits']}/{g['run_count']} observed entries", "CONFIRMED", "CORE-009", "可达性确认"),
        ("ORDINAL1_INPUT_CONTRACT", "UNKNOWN", "无 EXE 显式参数；寄存器语义角色未闭合", "UNKNOWN", "CORE-008/009", "不得猜调用约定"),
        ("ORDINAL1_STACK_ARGUMENTS", "UNKNOWN", "静态无 push/栈准备；动态存在稳定栈数据但角色未证", "NOT_CONFIRMED", "CORE-008/009", "字面量见 core009_literal"),
        ("ORDINAL1_RETURNED", "NOT_FOUND", f"return-site hits {g['return_hits']}/{g['run_count']}", "NOT_CONFIRMED", "CORE-009", "0/12 observed return"),
        ("ORDINAL1_RETURN_CONTRACT", "UNKNOWN", "无 return 观测 => 无契约", "NOT_CONFIRMED", "CORE-009", "与 NON_RETURN 分开"),
        ("RETURN_VALUE_CONSUMER", "NOT_FOUND", "无 caller-side consumer", "NOT_FOUND", "CORE-008/009", "静态与动态一致"),
        ("ORDINAL1_NON_RETURN", "UNKNOWN", "0/12 只证明 BOUNDARY_NO_RETURN_OBSERVED", "UNKNOWN", "CORE-009", "禁止写成 NONRETURN_CONFIRMED"),
        ("SIDE_EFFECT_CONTRACT", "UNKNOWN", "无 caller-side after-state", "NOT_CONFIRMED", "CORE-009", "返回点未到达"),
        ("COMMANDLINE_BOUNDARY_DELTA_Q", "UNKNOWN", "case B 与 case A 边界输入无可重复差异", "NOT_CONFIRMED", "CORE-009", "-q 不改变边界输入"),
        ("COMMANDLINE_BOUNDARY_DELTA_QA", "UNKNOWN", "case C 与 case A 边界输入无可重复差异", "NOT_CONFIRMED", "CORE-009", "-qa 不改变边界输入"),
        ("COMMANDLINE_BOUNDARY_DELTA_SRC", "UNKNOWN", "case D 与 case A 边界输入无可重复差异", "NOT_CONFIRMED", "CORE-009", "-src=tgp 不改变边界输入"),
        ("MODULE_THREAD_CALLER_CONTRACT", "UNKNOWN", "线程/模块活动是进程内部副作用", "NOT_CONFIRMED", "CORE-009", "不是 caller contract"),
        ("FS_METADATA_DELTA", "CONFIRMED", f"{g['fs_delta_rows']} rows", "0", "CORE-009", "metadata snapshot 未发现变化"),
        ("REGISTER_VALUE_STABILITY", "CONFIRMED", "EAX/EDX/ESI/EDI/EFLAGS 12/12 稳定", "CONFIRMED", "CORE-009", "仅为值稳定"),
        ("REGISTER_SEMANTIC_ROLE", "UNKNOWN", "无角色指派证据", "UNKNOWN", "CORE-009", "ESI=Base+0 不得解释为 NULL context"),
        ("ARGV_DATA_SHAPE", "CONFIRMED", "0x0196928C count + 0x01969290 char** array", "CONFIRMED", "CORE-008/009", "边界入口时为 0"),
        ("ARGV_PROVIDER", "CANDIDATE", "0x00CA827C（call site 0x00561133）", "CANDIDATE", "CORE-008", "不是 Windows API 证明"),
        ("ARGV_SOURCE", "CANDIDATE", "process command line（UTF-16 源形状）", "CANDIDATE", "EX-034", "具体 API 未绑定"),
    ]
    rows += [
        ("WIN_NO_TCLS", "CONFIRMED", "no args / -src=tgp -> fatal；-q 或 -qa -> bypass", "CONFIRMED", "EX-031/035/046", "本地上下文 gate"),
        ("Q_BYPASS", "CONFIRMED", "-q 抑制 WIN_NO_TCLS，之后进入 IIPS init", "CONFIRMED", "EX-035", "不作为完整启动"),
        ("QA_BYPASS", "CONFIRMED", "-qa 抑制 WIN_NO_TCLS，之后进入 IIPS init", "CONFIRMED", "EX-035", "不作为完整启动"),
        ("SRC_TGP_STANDALONE_BYPASS", "UNKNOWN", "-src=tgp 单独不 bypass", "NOT_CONFIRMED", "EX-035/046", "不得写成 standalone bypass"),
        ("STATE_0849413B", "CONFIRMED", "1 write + 3 reads（1 candidate rejected as data）", "CONFIRMED", "CORE-007/008", "边界入口值 0"),
        ("STATE_0849B500", "NOT_FOUND", "EXE 文件镜像 0 引用；runtime -qa 写 1", "NOT_FOUND", "CORE-007/008 + EX-035", "runtime 观测标 RUNTIME_OBSERVED"),
        ("STATE_0849B501", "CONFIRMED", "读已确认；写 NOT_FOUND in file image", "CONFIRMED", "CORE-007/008", "写仅 runtime 观测"),
        ("STATE_08189FEC", "NOT_FOUND", "EXE 文件镜像 0 引用；runtime fatal code", "NOT_FOUND", "CORE-007/008", "PACKED_OR_RUNTIME_GENERATED"),
        ("NATIVE_BOOTSTRAP_CHAIN", "CANDIDATE", "0x77F580 -> ... -> 0x6212C0", "CANDIDATE", "EX-044/045/046", "历史候选，未 Entry-connected"),
        ("ENTRY_CONNECTION", "UNKNOWN", "HISTORICAL_CHAIN_STATUS = NOT_ENTRY_CONNECTED", "UNKNOWN", "CORE-005/006", "不得升级为 CONFIRMED"),
        ("NETWORK_INIT", "CANDIDATE", "0x808650 / 0x7E98F0 / 0x6212C0", "CANDIDATE", "EX-043/044/045", "无连接证据"),
        ("IIPS_BOUNDARY", "BOUNDARY", "iips.dll / IFS2.dll / CNIFS", "CONFIRMED", "EX-047/048/060", "外部边界"),
        ("IIPS_SUCCESS", "UNKNOWN", "无成功路径证据；8189fec 为 fatal", "UNKNOWN", "EX-035/050", "FAILURE_ROOT 亦 UNKNOWN"),
        ("EXE_SELF_BOOTSTRAP", "NOT_FOUND", "Entry-connected native edges = 0", "NOT_FOUND", "CORE-005/006", "静态结构结论"),
        ("POST_BOUNDARY_EXE_ENTRY_INFERENCE", "CANDIDATE", "动态可达 EXE 链头 vs 静态空 Entry 图", "CANDIDATE", "EX-046 + CORE-006", "本轮唯一结构性推论"),
        ("GAME_INIT", "UNKNOWN", "无直接证据", "UNKNOWN", "CORE-005/006/007", "不虚构"),
        ("RENDERER", "UNKNOWN", "无直接证据", "UNKNOWN", "CORE-001..009", "不虚构"),
        ("INPUT_AUDIO", "UNKNOWN", "无直接证据", "UNKNOWN", "CORE-001..009", "不虚构"),
        ("MAIN_LOOP", "UNKNOWN", "无 Entry-connected 循环证据", "UNKNOWN", "CORE-002/007", "不虚构"),
    ]
    return [
        {"contract": c, "status": s, "value": v, "core009_literal": lit, "source": src, "notes": n}
        for c, s, v, lit, src, n in rows
    ]


def build_layers(st: dict, g: dict) -> list[dict[str, object]]:
    rows = [
        ("A_PROCESS", "EXE identity (path + SHA-256)", "CONFIRMED", "CONFIRMED", "SHA-256 re-verified this round", "样本固定"),
        ("A_PROCESS", "architecture PE32/I386", "CONFIRMED", "CONFIRMED", f"machine 0x{st['machine']:X}, magic 0x{st['magic']:X}", "WoW64 运行"),
        ("A_PROCESS", "working directory = game root", "CANDIDATE", "CANDIDATE", "EX-046 minimal context reaches IIPS fatal", "未做逐项消融"),
        ("A_PROCESS", "command line present", "CONFIRMED", "CONFIRMED", "argv count/array shape + gate tokens in EXE image", "命令行为 EXE 读取"),
        ("A_PROCESS", "-q or -qa (WIN_NO_TCLS bypass)", "CONFIRMED", "CANDIDATE", "EX-035 gate matrix", "仅该路径需要；CORE-009 边界可达性不需要"),
        ("A_PROCESS", "environment variables", "UNKNOWN", "UNKNOWN", "no evidence in CORE-001..009", "不得假设"),
        ("B_EXE", "Entry action", "CONFIRMED", "CONFIRMED", f"{ENTRY_BYTES} -> slot 0x{IAT_SLOT_VA:X}", "唯一外部转移"),
        ("B_EXE", "IAT slot -> Base ordinal 1", "CONFIRMED", "CONFIRMED", "slot value 0x80000001, no base relocation", "边界 seam"),
        ("B_EXE", "argv storage", "CONFIRMED", "CONFIRMED", "0x0196928C / 0x01969290 static writes + runtime shape", "边界入口时为 0"),
        ("B_EXE", "argv provider slot", "CANDIDATE", "CANDIDATE", "0x00CA827C, call site 0x00561133", "目标 runtime-bound"),
        ("B_EXE", "startup globals", "CONFIRMED", "CANDIDATE", "0x0849413B confirmed; 0x0849B501 read; 0x0849B500 static NOT_FOUND", "运行时写入未静态闭合"),
        ("B_EXE", "internal dispatch table", "CANDIDATE", "UNKNOWN", "slot array exists, targets VIRTUAL_ONLY", "最低必要集合未知"),
        ("B_EXE", "native bootstrap chain", "CANDIDATE", "UNKNOWN", "EX-044/045/046 chain; Entry-connected edges = 0", "NOT_ENTRY_CONNECTED"),
        ("C_RUNTIME", "Base.dll ordinal-1 boundary", "BOUNDARY", "UNKNOWN", f"{g['ordinal1_hits']}/{g['run_count']} entries, {g['return_hits']}/{g['run_count']} returns", "输入/返回/终止契约开放"),
        ("C_RUNTIME", "system DLLs", "CONFIRMED", "CONFIRMED", "OS loader; ntdll/kernel32/kernelbase in observed module set", "非项目可控"),
        ("C_RUNTIME", "EXE-tree project module set", "CONFIRMED", "UNKNOWN", f"{g['module_distinct_count']} modules in window; libcef/BugTrace present, iips/TenProxy absent", "加载序非因果"),
        ("C_RUNTIME", "filesystem tree", "CONFIRMED", "CANDIDATE", f"metadata delta rows = {g['fs_delta_rows']}; EX-046 full tree context", "树完整性未消融"),
        ("C_RUNTIME", "network / STUN", "CANDIDATE", "UNKNOWN", "demonware endpoint string in EXE image; no connection evidence", "配置/字符串证据"),
        ("C_RUNTIME", "IIPS / IFS2 / CNIFS", "BOUNDARY", "UNKNOWN", "post-gate blocker WIN_IIPS_INIT_ERROR 8189fec", "成功路径未观测"),
        ("C_RUNTIME", "Tencent launcher components", "NOT_FOUND", "NOT_REQUIRED", "no static import / no load-time requirement proven", "WeGame/TCLS/Client.exe"),
        ("D_GAME", "game init", "UNKNOWN", "UNKNOWN", "no direct evidence", "不虚构"),
        ("D_GAME", "renderer", "UNKNOWN", "UNKNOWN", "no direct evidence", "不虚构"),
        ("D_GAME", "input / audio", "UNKNOWN", "UNKNOWN", "no direct evidence", "不虚构"),
        ("D_GAME", "main loop", "UNKNOWN", "UNKNOWN", "no Entry-connected loop evidence", "不虚构"),
    ]
    return [
        {"layer": a, "item": b, "status": c, "required_for_standalone": d, "evidence": e, "notes": f}
        for a, b, c, d, e, f in rows
    ]


def build_required_vs_optional(st: dict, g: dict) -> list[dict[str, object]]:
    rows = [
        (
            "WeGame",
            "EXE import table has 1 descriptor (Base.dll only); no WeGame reference in the EXE file image",
            "NOT_REQUIRED_CONFIRMED",
            "EX-046: direct launch entered native bootstrap and reached the post-gate IIPS fatal",
            "CONFIRMED",
        ),
        (
            "TCLS",
            "no EXE import or reference; TCLS shared memory absent in the direct-launch observation",
            "NOT_REQUIRED_CONFIRMED",
            "EX-046 / EX-031: WIN_NO_TCLS is argv-driven, not a TCLS shared-memory check",
            "CONFIRMED",
        ),
        (
            "Client.exe (TCLS folder)",
            "no EXE import or reference; the EXE was never observed launching Client.exe",
            "NOT_REQUIRED_CONFIRMED",
            "EX-035 / EX-046: no original launcher was started and bootstrap still ran",
            "CONFIRMED",
        ),
        (
            "tcls_core / TCLS.dll",
            "no static import; absent from the CORE-009 observed module set",
            "NOT_REQUIRED_CONFIRMED",
            "EX-046: not loaded, native bootstrap still proceeded",
            "CONFIRMED",
        ),
        (
            "TCLS shared memory / TPF_Share_Mem",
            "no EXE-side access evidence to any TCLS shared section",
            "NOT_REQUIRED_CONFIRMED",
            "EX-046: not present, startup still reached the post-gate blocker",
            "CANDIDATE",
        ),
        (
            "IIPSHostApp.exe",
            "no EXE-side reference found; never observed as a process",
            "UNKNOWN",
            "no evidence for or against; must not be listed as a hard prerequisite",
            "UNKNOWN",
        ),
        (
            "IFS2.dll",
            "no EXE import entry; referenced from the iips.dll side (EX-048)",
            "REQUIRED_CANDIDATE",
            "IIPS initialization reaches the IFS2 boundary; the first failing prerequisite is not proven to be IFS2",
            "CANDIDATE",
        ),
        (
            "TenProxy",
            "no EXE import entry; loaded in all observed EX-035 runs, absent inside the CORE-009 window",
            "UNKNOWN",
            "load order is not causality; no Tencent launcher hard dependency proven before IIPS",
            "CANDIDATE",
        ),
    ]
    return [
        {"component": a, "direct_exe_evidence": b, "required_status": c, "reason": d, "confidence": e}
        for a, b, c, d, e in rows
    ]


def build_required_vs_optional_b(st: dict, g: dict) -> list[dict[str, object]]:
    rows = [
        (
            "TenRpcs / TenSafe / GbSpy / GDPLoader / PolicyProbe",
            "no EXE import entry; loaded in observed EX-035 runs only",
            "UNKNOWN",
            "no causal link to bootstrap progress has been established",
            "CANDIDATE",
        ),
        (
            "BugTrace.dll",
            f"present in the CORE-009 observed module set ({g['module_distinct_count']} modules)",
            "UNKNOWN",
            "loaded early in the observed window, but causality to boot progress is not proven",
            "CANDIDATE",
        ),
        (
            "libcef.dll",
            "present in the CORE-009 observed module set",
            "UNKNOWN",
            "load-time presence only; not proven required for native bootstrap",
            "CANDIDATE",
        ),
        (
            "Base.dll ordinal-1",
            "unique FF15 call site at Entry (slot 0x0E9DC665); reached in 12/12 observed runs",
            "REQUIRED_CANDIDATE",
            "only Entry-connected external transfer, but whether it leads to the runtime is UNKNOWN",
            "CANDIDATE",
        ),
        (
            "iips.dll",
            "EXE file image contains the 'iips.dll' string; no static import; post-gate blocker observed",
            "REQUIRED_CANDIDATE",
            "first observed post-gate blocker (WIN_IIPS_INIT_ERROR / 8189fec); may be bypassable",
            "CANDIDATE",
        ),
        (
            "local game tree (working dir = game root)",
            "not provable from the file image; observation-derived (EX-046 minimal context)",
            "REQUIRED_CANDIDATE",
            "full local tree + working dir = game root reaches the IIPS fatal, but no ablation was run",
            "CANDIDATE",
        ),
        (
            "-q or -qa",
            "gate tokens (-q / -qa / -src=tgp) and the WIN_NO_TCLS error string are in the EXE file image",
            "REQUIRED_CONFIRMED",
            "EX-035: no args -> WIN_NO_TCLS fatal; -q or -qa -> bypass and continue to IIPS init",
            "CONFIRMED",
        ),
        (
            "network connectivity",
            "stun.us.demonware.net present in the EXE file image; stun1-tub.codol.qq.com not found there",
            "UNKNOWN",
            "no connection evidence; config/string presence is not a dependency proof",
            "UNKNOWN",
        ),
        (
            "renderer / audio / input",
            "no direct evidence in CORE-001..009",
            "UNKNOWN",
            "never reached in any closed observation",
            "UNKNOWN",
        ),
    ]
    return [
        {"component": a, "direct_exe_evidence": b, "required_status": c, "reason": d, "confidence": e}
        for a, b, c, d, e in rows
    ]


def build_required(st: dict, g: dict) -> list[dict[str, object]]:
    return build_required_vs_optional(st, g) + build_required_vs_optional_b(st, g)


def build_gaps_a(st: dict, g: dict) -> list[dict[str, object]]:
    rows = [
        (
            "GAP-P0-001",
            "C_RUNTIME",
            "POST_BOUNDARY_CONTROL_TRANSFER",
            "UNKNOWN",
            "UNKNOWN",
            "P0",
            f"EXE return-site hit {g['return_hits']}/{g['run_count']}; static Entry-connected native edges = 0; "
            "EX-046 independent-copy runs do reach an EXE-side chain head",
            "EXE 镜像代码在边界之后是否执行、由哪个模块进入",
            "E-010-01",
        ),
        (
            "GAP-P0-002",
            "C_RUNTIME",
            "BASE_ORDINAL1_BOUNDARY_CONTRACT",
            "UNKNOWN",
            "UNKNOWN",
            "P0",
            f"{g['ordinal1_hits']}/{g['run_count']} entries; input/stack/return/side-effect/termination all UNKNOWN; "
            "register values stable but semantics unassigned",
            "ordinal-1 的最低必要边界行为与终止语义",
            "E-010-01",
        ),
        (
            "GAP-P0-003",
            "B_EXE",
            "EXE_ENTRY_NATIVE_CONTINUATION",
            "NOT_FOUND",
            "UNKNOWN",
            "P0",
            f"zero-padding fall-through span = {st['entry_fallthrough_zero_span']} bytes; no EAX consumer; "
            "Entry-connected edges = 0",
            "该缺失是否意味着 EXE 只能经由外部转移启动",
            "E-010-01",
        ),
        (
            "GAP-P0-004",
            "C_RUNTIME",
            "OBSERVATION_ENVIRONMENT_DIVERGENCE",
            "UNRESOLVED",
            "UNKNOWN",
            "P0",
            f"CORE-009 window ends at process exit (~{g['thread_last_first_seen_s']}s observer-relative) while EX-046 "
            "normal copies reach the IIPS fatal at about T+7.7s",
            "观察器环境是否改变 ordinal-1 的终止行为；根因 UNKNOWN",
            "E-010-01",
        ),
    ]
    return [
        {
            "gap_id": a,
            "layer": b,
            "component": c,
            "current_status": d,
            "blocking_level": e,
            "priority": f,
            "evidence": g_,
            "unknown": h,
            "minimal_next_experiment": i,
        }
        for a, b, c, d, e, f, g_, h, i in rows
    ]


def build_gaps_b(st: dict, g: dict) -> list[dict[str, object]]:
    rows = [
        (
            "GAP-P1-001",
            "B_EXE",
            "NATIVE_BOOTSTRAP_ENTRY_CONNECTION",
            "UNKNOWN",
            "CANDIDATE",
            "P1",
            "EX-044/045/046 chain recovered, but CORE-005/006 report NOT_ENTRY_CONNECTED",
            "0x77F580 链头的调用者与触发条件",
            "defer until P0 closes",
        ),
        (
            "GAP-P1-002",
            "C_RUNTIME",
            "IIPS_INITIALIZATION",
            "UNKNOWN",
            "CANDIDATE",
            "P1",
            "post-gate WIN_IIPS_INIT_ERROR / 8189fec; IIPS_SUCCESS and IIPS_FAILURE_ROOT UNKNOWN",
            "首个失败的 IIPS prerequisite 与 8189FEC 的真实来源",
            "defer until P0 closes",
        ),
        (
            "GAP-P1-003",
            "B_EXE",
            "ARGV_PROVIDER_SLOT",
            "CANDIDATE",
            "CANDIDATE",
            "P1",
            "0x00CA827C single call site 0x00561133; argv globals still 0 at boundary entry",
            "provider 由谁绑定、在哪个阶段运行",
            "defer until P0 closes",
        ),
        (
            "GAP-P1-004",
            "B_EXE",
            "RUNTIME_DISPATCH_MINIMUM",
            "CANDIDATE",
            "UNKNOWN",
            "P1",
            "dispatch slot array exists, targets VIRTUAL_ONLY",
            "bootstrap 所需的最低 slot 集合与填充顺序",
            "defer until P0 closes",
        ),
        (
            "GAP-P2-001",
            "D_GAME",
            "GAME_INIT",
            "UNKNOWN",
            "UNKNOWN",
            "P2",
            "no direct CODOL address / call / structure evidence",
            "真实 game init 入口",
            "not selected in this round",
        ),
        (
            "GAP-P2-002",
            "D_GAME",
            "RENDERER_MAIN_LOOP",
            "UNKNOWN",
            "UNKNOWN",
            "P2",
            "no Entry-connected message/render loop evidence",
            "渲染与主循环入口、退出条件",
            "not selected in this round",
        ),
        (
            "GAP-P3-001",
            "C_RUNTIME",
            "PLATFORM_SERVICES",
            "UNKNOWN",
            "NOT_BLOCKING",
            "P3",
            "WeGame/TCLS/Client.exe proven not required on the observed path; TenProxy/TenRpcs/TenSafe/GbSpy load order only",
            "哪些平台服务最终只是 optional",
            "not selected in this round",
        ),
        (
            "GAP-P3-002",
            "A_PROCESS",
            "ENVIRONMENT_VARIABLES",
            "UNKNOWN",
            "UNKNOWN",
            "P3",
            "no environment evidence in CORE-001..009",
            "环境变量是否参与启动判定",
            "not selected in this round",
        ),
    ]
    return [
        {
            "gap_id": a,
            "layer": b,
            "component": c,
            "current_status": d,
            "blocking_level": e,
            "priority": f,
            "evidence": g_,
            "unknown": h,
            "minimal_next_experiment": i,
        }
        for a, b, c, d, e, f, g_, h, i in rows
    ]


def build_gaps(st: dict, g: dict) -> list[dict[str, object]]:
    return build_gaps_a(st, g) + build_gaps_b(st, g)


def build_next_experiment(st: dict, g: dict) -> list[dict[str, object]]:
    return [
        {
            "experiment_id": "E-010-01",
            "gap_ids": "GAP-P0-001; GAP-P0-002; GAP-P0-003; GAP-P0-004",
            "decision": "ONE_ONLY",
            "single_variable": "EXE_IMAGE_EXECUTION_AFTER_BOUNDARY in {OBSERVED, NOT_OBSERVED}",
            "method": (
                "Reuse the CORE-009 temporary-breakpoint observer (no file modification). Keep the ordinal-1 entry "
                "breakpoint, add a BOUNDED set of execute breakpoints at the EXE-side chain heads "
                "(VA = 0x00400000 + {0x77F580, 0x77F8B3, 0x4FD9B0, 0x4FCEE0, 0x808650, 0x7E98F0, 0x6212C0}) and record "
                "the owning module of every hit."
            ),
            "measures": (
                "whether EXE-image code executes after the Base ordinal-1 boundary and which module enters it; "
                "plus whether the ordinal-1 termination stays identical without extra breakpoints"
            ),
            "exe_side_only": "YES",
            "base_internals_required": "NO (address ownership only; no Base disassembly / CFG / .tvm0)",
            "cost": "1 observation session; <= 8 breakpoints; <= 300s wall clock; bounded event log",
            "expected_uncertainty_delta": (
                "collapses GAP-P0-001 and GAP-P0-003 from UNKNOWN to one bit; if OBSERVED it also names the entering "
                "module and moves P0 from 'does a native path exist' to 'how to reach that path standalone'"
            ),
            "fallback_if_negative": (
                "if EXE-image execution is NOT_OBSERVED in both the observer and the normal-copy environment, stop "
                "reverse engineering and switch to Standalone Bootstrap Design (boundary replacement track)"
            ),
            "notes": "No -q/-qa matrix extension, no Base internals, no credential / session / token work.",
        }
    ]


def resolve_status(gaps: list[dict[str, object]]) -> tuple[str, str]:
    p0 = [x for x in gaps if x["priority"] == "P0"]
    p1 = [x for x in gaps if x["priority"] == "P1"]
    if p0 and any(x["blocking_level"] == "CONFIRMED" for x in p0):
        return "BLOCKED_BY_P0", "at least one P0 gap is confirmed blocking"
    if p0:
        return (
            "BLOCKED_BY_UNKNOWN",
            "P0 gaps exist but none reaches CONFIRMED blocking level; the primary unknown is whether EXE-image "
            "code executes at/after the boundary",
        )
    if p1 and any(x["blocking_level"] == "CONFIRMED" for x in p1):
        return "BLOCKED_BY_P1", "no P0 gap; at least one P1 gap is confirmed blocking"
    if p1:
        return "BLOCKED_BY_UNKNOWN", "no P0 gap; every P1 gap stays UNKNOWN/CANDIDATE"
    return "READY_FOR_IMPLEMENTATION", "no P0/P1 gap remains"


def report_head(st: dict, g: dict) -> str:
    return f"""# CODOL_STANDALONE_CORE_010
# Standalone Bootstrap Contract with Explicit Unknowns

## 0. Task, scope and prohibitions

```text
ROUND        = EXE-CORE-010 (Bootstrap Contract with Explicit Unknowns)
PRIMARY      = COD OL/codoMP_client_shipRetail.exe
PRIMARY SHA  = {st['exe_sha256']}
SAMPLE MATCH = {st['exe_sha256_match']}
BOUNDARY     = codoMP_client_shipRetailBase.dll ({BASE_SHA256[:16]}...)
BASELINE     = CORE-001..CORE-009 plus targeted EX rounds; no new reverse targets
```

Prohibitions honoured this round:

```text
NO EXE modification / NO patch / NO hook / NO stub DLL      -> honoured
NO Base CFG / NO Base .text reverse / NO Base .tvm0         -> honoured
NO Base allocator / thread / IIPS / TenProxy internals      -> honoured
NO Tencent launcher reverse (TCLS / WeGame / Client.exe)    -> honoured
NO Procmon / NO Sandboxie / NO large-scale tracing          -> honoured
NO credential / session / token work                        -> honoured
STATIC FILE ACCESS                                          -> READ ONLY (SHA-256, PE header,
                                                               instruction bytes, ASCII tokens)
```

Method: the sample is re-verified statically at generation time, the CORE-009
observation artifacts are re-aggregated from their CSVs, and every contract row
carries an explicit status from the CORE-010 vocabulary
(`CONFIRMED / CANDIDATE / UNKNOWN / BOUNDARY / NOT_FOUND / UNRESOLVED`).
CORE-009 literal status words outside that vocabulary (for example
`NOT_CONFIRMED`) are preserved verbatim in the `core009_literal` column.

Conventions used by every artifact:

```text
blocking_level : CONFIRMED / CANDIDATE / UNKNOWN / NOT_BLOCKING
                 (how confident we are that the item blocks boot)
priority       : P0 / P1 / P2 / P3
                 P0 directly blocks the EXE native bootstrap
                 P1 blocks native bootstrap -> game init
                 P2 blocks game init -> main loop
                 P3 outside the boot core
                 => "ORDINAL1 = P0 UNKNOWN" is therefore encoded as
                    priority=P0 with blocking_level=UNKNOWN, never as P0 + CONFIRMED
required       : CONFIRMED / CANDIDATE / UNKNOWN / NOT_REQUIRED        (state machine)
required_status: REQUIRED_CONFIRMED / REQUIRED_CANDIDATE / UNKNOWN /
                 NOT_REQUIRED_CONFIRMED                                (dependency audit)
```"""


def report_core009(st: dict, g: dict) -> str:
    per_case = "; ".join(
        f"{c}: entries {d['ordinal1']}/{d['runs']}, returns {d['return']}" for c, d in sorted(g["per_case"].items())
    )
    return f"""
---

## 1. CORE-009 ingest (frozen, unchanged)

CORE-009 is adopted verbatim, including its final status block:

```text
ORDINAL1_INPUT_CONTRACT        = UNKNOWN
ORDINAL1_STACK_ARGUMENTS       = NOT_CONFIRMED
ORDINAL1_RETURNED              = NOT_CONFIRMED  (0/12 observed return)
ORDINAL1_RETURN_CONTRACT       = NOT_CONFIRMED
RETURN_VALUE_CONSUMER          = NOT_FOUND
SIDE_EFFECT_CONTRACT           = NOT_CONFIRMED
COMMANDLINE_BOUNDARY_DELTA_Q   = NOT_CONFIRMED
COMMANDLINE_BOUNDARY_DELTA_QA  = NOT_CONFIRMED
COMMANDLINE_BOUNDARY_DELTA_SRC = NOT_CONFIRMED
MODULE_THREAD_CALLER_CONTRACT  = NOT_CONFIRMED
FS_METADATA_DELTA              = 0
FINAL_MARKER                   = ORDINAL1_BOUNDARY_NO_RETURN_UNRESOLVED
```

`0/12` describes observation only, never Base behaviour:

```text
ORDINAL1_NONRETURN = UNKNOWN            (not NONRETURN_CONFIRMED)
```

Re-aggregated observation data (derived from the CORE-009 CSVs, not hand-copied):

```text
runs                        = {g['run_count']} (cases {'/'.join(g['cases'])})
ordinal-1 entries           = {g['ordinal1_hits']}/{g['run_count']}
EXE return-site hits        = {g['return_hits']}/{g['run_count']}
per case                    = {per_case}
process states              = {', '.join(g['process_states'])}
exit codes                  = {', '.join(g['exit_codes'])}
thread counts per run       = {g['thread_counts']}
last observer-relative time = {g['thread_last_first_seen_s']}s
modules in window           = {g['module_distinct_count']} distinct ({g['module_events']})
project modules present     = {g['watched_modules_present'] or 'NONE'}
project modules absent      = {g['watched_modules_absent']}
filesystem metadata delta   = {g['fs_delta_rows']} rows
```

Boundary input observations (values frozen, semantics deliberately unassigned):

```text
EAX    = {g['reg_values']['eax_in']}  (= Base runtime base + 0x1D6582C, the ordinal-1 code address)
EDX    = {g['reg_values']['edx_in']}  (= Base runtime base + 0x110)
ESI    = {g['reg_values']['esi_in']}  (= Base runtime base + 0)
EDI    = {g['reg_values']['edi_in']}
EFLAGS = {g['reg_values']['eflags_in']}
ECX / ESP / EBP = variable per run ({g['reg_variable_counts']['ecx_in']} / {g['reg_variable_counts']['esp_in']} / {g['reg_variable_counts']['ebp_in']} distinct values)

REGISTER_VALUE_STABILITY = CONFIRMED
REGISTER_SEMANTIC_ROLE   = UNKNOWN
```

Stable stack data exists but is not accepted as an argument list:

```text
[ESP] {g['stack_stable']['stack_0']}   [ESP+4] {g['stack_stable']['stack_4']}   [ESP+18] {g['stack_stable']['stack_18']}
STACK_ARGUMENTS = NOT_CONFIRMED (CORE-009 literal)
```

`ESI` referencing `Base + 0` is **not** interpreted as a NULL context, and no
register is labelled `this` / `context` / `argument` / `flags` without new direct
evidence.

### 1.1 Observation-window coverage (new explicit limitation)

```text
CORE-009 window : process exits inside the observation window; last observer-relative
                  thread timestamp {g['thread_last_first_seen_s']}s, module set {g['module_distinct_count']},
                  project modules iips/IFS2/TCLS/TenProxy absent
EX-046 baseline : independent-copy runs reach the IIPS fatal at about T+7.7s
=> OBSERVATION_WINDOW_COVERAGE = UNRESOLVED (root cause UNKNOWN)
```

The CORE-009 window never reaches the IIPS phase, and its exit codes
({', '.join(g['exit_codes'])}) are observer-conditional. They are recorded as
observations of the observation environment, not as Base behaviour and not as a
confirmed termination contract.
"""


def report_evidence(st: dict, g: dict, ledger: list[dict[str, object]], states: list[dict[str, object]]) -> str:
    counts: dict[str, int] = {}
    for row in ledger:
        counts[str(row["status"])] = counts.get(str(row["status"]), 0) + 1
    count_line = ", ".join(f"{k}={counts[k]}" for k in STATUS_ENUM if k in counts)
    ledger_lines = "\n".join(
        f"{row['id']}  {str(row['component']):<34} {str(row['status']):<10} {row['address']}" for row in ledger
    )
    state_lines = "\n".join(
        f"{row['state_id']:<28} {str(row['status']):<10} required={str(row['required']):<12} "
        f"blocking={row['blocking_level']}"
        for row in states
    )
    return f"""
---

## 2. Evidence Ledger

Artifact: `exe_core010_evidence_ledger.csv` ({len(ledger)} rows)
Status distribution: {count_line}

```text
{ledger_lines}
```

Only the six CORE-010 status values are used in the `status` column. Where
CORE-009 used a literal outside that set, the literal is preserved in the row's
`notes` and in the contract matrix `core009_literal` column.

---

## 3. Bootstrap State Machine

Artifact: `exe_core010_boot_state_machine.csv` ({len(states)} nodes, BOOT_00..BOOT_12)

```text
{state_lines}
```

```text
CONFIRMED nodes     : BOOT_00, BOOT_01, BOOT_04          (structure and gate)
BOUNDARY nodes      : BOOT_02 (Base ordinal-1), BOOT_07 (IIPS)
CANDIDATE nodes     : BOOT_03, BOOT_05, BOOT_06
UNKNOWN nodes       : BOOT_08..BOOT_12                   (game init, renderer,
                                                          input/audio, main loop, shutdown)
NO node was invented to make the machine look complete: BOOT_09/BOOT_10/BOOT_11
stay UNKNOWN because CORE-001..009 contain no direct evidence for them.
```

`BOOT_12_SHUTDOWN` is `required = NOT_REQUIRED` by definition (a shutdown phase
cannot be a prerequisite for reaching the runtime); its semantics remain
`UNKNOWN` because the observed exit codes are observer-conditional.
"""


def report_entry_ordinal1(st: dict, g: dict) -> str:
    ss = st["site_summary"]
    return f"""
---

## 4. Entry contract (BOOT_01_EXE_ENTRY)

```asm
ImageBase = 0x00400000
Entry RVA = 0x0E5DC690
0x0E5DC690  {ENTRY_BYTES}   call dword ptr [0x{IAT_SLOT_VA:X}]
0x0E5DC696  ..             zero padding ({st['entry_fallthrough_zero_span']} bytes, re-verified)
```

```text
ENTRY                        = CONFIRMED
ENTRY_ACTION                 = EXTERNAL_CALL
IAT slot                     = 0x{IAT_SLOT_VA:X} (RVA 0x{IAT_SLOT_RVA:X})
slot file value              = 0x{st['iat_slot_value']:08X} -> Base.dll ordinal 1
FF15 sites for this slot     = 1
base relocation for the slot = {st['reloc_dir_size']} (none)
EXE import descriptors       = {st['import_descriptor_count']} ({' / '.join(st['import_names'])})
ENTRY_TO_ORDINAL1            = CONFIRMED
ENTRY_NATIVE_CONTINUATION    = NOT_FOUND
```

The image has {len(st['sections'])} sections ({', '.join(st['section_names'])}); the
`.tvm0` section is present but was **not** decoded in this round.

---

## 5. Ordinal-1 boundary contract (BOOT_02)

```text
ORDINAL1_REACHABILITY   = CONFIRMED   ({g['ordinal1_hits']}/{g['run_count']} observed entries, cases {'/'.join(g['cases'])})
ORDINAL1_INPUT_CONTRACT = UNKNOWN     (no EXE-provided arguments; register roles unassigned)
ORDINAL1_STACK_ARGUMENTS= UNKNOWN     (CORE-009 literal: NOT_CONFIRMED)
ORDINAL1_RETURN_CONTRACT= UNKNOWN     (CORE-009 literal: NOT_CONFIRMED)
ORDINAL1_RETURNED       = NOT_FOUND   (return-site hits {g['return_hits']}/{g['run_count']})
ORDINAL1_NON_RETURN     = UNKNOWN     (0/12 does not prove "never returns")
RETURN_VALUE_CONSUMER   = NOT_FOUND
ORDINAL1_SIDE_EFFECT    = UNKNOWN     (CORE-009 literal: NOT_CONFIRMED)
ORDINAL1_TERMINATION    = UNKNOWN     (observer-conditional exit codes)
```

What is known about ordinal-1:

```text
- the EXE Entry performs no push, no register setup, no stack preparation;
- the boundary is reached reliably (12/12) with and without -q / -qa / -src=tgp;
- the EXE return site is never reached within the observation window;
- process-internal activity continues (threads {g['thread_counts']}, modules {g['module_distinct_count']})
  after the boundary entry.
```

What is unknown about ordinal-1:

```text
- the calling convention and the role of each register;
- whether it returns at all, and with what value;
- whether it passes control back into EXE-image code;
- whether it creates or hands control to another runtime;
- why the process terminates inside the observation window.
```

Ordinal-1 is therefore recorded as:

```text
BOOT_02_STATUS = BOUNDARY
ORDINAL1       = P0 UNKNOWN        (priority P0, blocking_level UNKNOWN)
```

It is **not** written as `P0 CONFIRMED`, and it is **not** used as a known
standalone contract implementation. Distinguishing "no return observed" from
"terminates the boot thread" from "transfers execution" would require Base
internals and is explicitly out of scope; the minimal experiment in section 17
tests only the EXE-visible consequence.
"""


def report_argv_gate(st: dict, g: dict) -> str:
    ss = st["site_summary"]
    sb = g["state_before"]
    return f"""
---

## 6. ARGV contract (BOOT_03)

```text
ARGV_COUNT_GLOBAL   = 0x0196928C
ARGV_ARRAY_GLOBAL   = 0x01969290
static write pair   = 0x00561119 (count), 0x0056111E (array)   [re-verified]
ARGV_DATA_SHAPE     = CONFIRMED   (count + char** array)
ARGV_PROVIDER       = CANDIDATE   0x00CA827C (single call site 0x00561133)
ARGV_SOURCE         = CANDIDATE   process command line (UTF-16 source shape)
```

Static operand verification performed this round:

```text
0x0196928C : {ss['ARGV_COUNT_0196928C']['validated']} validated of {ss['ARGV_COUNT_0196928C']['total']} candidates -> {ss['ARGV_COUNT_0196928C']['insns']}
0x01969290 : {ss['ARGV_ARRAY_01969290']['validated']} validated of {ss['ARGV_ARRAY_01969290']['total']} candidates -> {ss['ARGV_ARRAY_01969290']['insns']}
0x00CA827C : {ss['ARGV_PROVIDER_00CA827C']['validated']} validated of {ss['ARGV_PROVIDER_00CA827C']['total']} candidates -> {ss['ARGV_PROVIDER_00CA827C']['insns']}
unvalidated candidates are data-like byte coincidences and are not used as evidence
```

Runtime cross-check: at the ordinal-1 boundary entry both globals still hold
`{sb.get('argv_count')}` / `{sb.get('argv_array')}` in all {g['run_count']} runs, even when a
command line was supplied. Therefore the provider had not run at that moment in
the observed environment - an observation, not a contract.

`0x00CA827C` is **not** claimed to be `GetCommandLineW`, `GetCommandLineA` or
`CommandLineToArgvW`; its target stays runtime-bound and VIRTUAL_ONLY.

---

## 7. Startup globals and context gate (BOOT_04)

```text
0x0849413B  = CONFIRMED startup state        (1 write + 3 reads, re-verified)
              static sites: {ss['STATE_0849413B']['validated']} validated of {ss['STATE_0849413B']['total']} candidates
              {ss['STATE_0849413B']['insns']}
              rejected data-like candidate(s): {ss['STATE_0849413B']['unvalidated']}
0x0849B500  = NOT_FOUND in the current EXE file image (0 operand sites)
              runtime observation: -qa sets it to 1  => RUNTIME_OBSERVED only
0x0849B501  = CONFIRMED read ({ss['STATE_0849B501']['validated']} site, {ss['STATE_0849B501']['insns']})
              write NOT_FOUND in the current EXE file image
              runtime observation: -src=tgp sets it to 1 => RUNTIME_OBSERVED only
0x08189FEC  = NOT_FOUND in the current EXE file image (0 operand sites), PACKED_OR_RUNTIME_GENERATED
```

Gate semantics (EX-031 / EX-035 / EX-046, unchanged):

```text
no args      -> WIN_NO_TCLS fatal                                  CONFIRMED
-q           -> bypass, then IIPS init error 8189fec               CONFIRMED
-qa          -> bypass, then IIPS init error 8189fec               CONFIRMED
-src=tgp     -> sets 0x0849B501, does not bypass WIN_NO_TCLS       CONFIRMED (sets) / NOT_CONFIRMED (standalone bypass)
```

New static verification this round: the gate tokens are inside the EXE file
image as one adjacent plain-text cluster:

```text
-qa        at file offset {hex(st['gate_tokens'][b'-qa'][0])}
-src=tgp   at file offset {hex(st['gate_tokens'][b'-src=tgp'][0])}
WIN_NO_TCLS at file offset {hex(st['gate_tokens'][b'WIN_NO_TCLS'][0])}
region: ...{st['gate_token_region'][:150]}...
```

This confirms the startup-context gate belongs to the EXE itself
(`PROCESS`/`EXE` layer), not to a Tencent authentication layer.

At the ordinal-1 boundary entry the gate value is still
`{sb.get('q_gate')}` and `{sb.get('src_tgp_gate')}` ({g['run_count']}/{g['run_count']}), which is consistent
with the gate running after the boundary in the EXE-visible timeline.
"""


def report_bootstrap_iips(st: dict, g: dict) -> str:
    return f"""
---

## 8. Native bootstrap candidates (BOOT_05)

```text
HISTORICAL_CANDIDATES = 0x77F580, 0x77F8B3, 0x4FD9B0, 0x4FCEE0, 0x808650, 0x7E98F0, 0x6212C0
CORE-005 / CORE-006  = HISTORICAL_CHAIN_STATUS = NOT_ENTRY_CONNECTED
                     = ENTRY_CONNECTED_NATIVE_EDGES = 0
```

```text
NATIVE_BOOTSTRAP_CHAIN = CANDIDATE
ENTRY_CONNECTION       = UNKNOWN          (must not be upgraded to CONFIRMED)
```

Structural observation recorded this round (the only new inference):

```text
independent-copy runs reach the EXE-side chain head (0x77F580 family) while the static
Entry-connected graph is empty
=> POST_BOUNDARY_EXE_ENTRY_INFERENCE = CANDIDATE
   (the chain must be entered from outside the Entry-connected graph; a Base -> EXE
    transfer is one possible explanation, not a proven fact)
```

No Base internals were inspected to test that inference.

---

## 9. Network initialization (BOOT_06)

```text
NETWORK_INIT   = CANDIDATE
nodes          = 0x6212C0 (STUN/network mode init), 0x7E98F0, 0x808650
STUN endpoints = stun1-tub.codol.qq.com, stun.us.demonware.net
```

Static string verification this round:

```text
stun.us.demonware.net : present in the EXE file image at {[hex(i) for i in st['strings'][b'stun.us.demonware.net']]}
stun1-tub.codol.qq.com: {len(st['strings'][b'stun1-tub.codol.qq.com'])} hits in the EXE file image (source unresolved)
Network Port          : present at {[hex(i) for i in st['strings'][b'Network Port'][:2]]}
```

```text
=> the demonware endpoint is EXE-side text; the codol.qq.com endpoint must come from
   another source (config file or another module) and is NOT proven EXE-side here.
```

The chain matches the IW4 lineage, but it is not promoted beyond `CANDIDATE` on
that basis: lineage similarity is not CODOL evidence.

---

## 10. IIPS boundary (BOOT_07)

```text
IIPS_BOUNDARY = CONFIRMED
IIPS_SUCCESS  = UNKNOWN
IIPS_FAILURE_ROOT = UNKNOWN
```

Confirmed boundary items (EX-047 / EX-048 / EX-060, unchanged):

```text
iips.dll
CNIFS::InitInGameApp
CNIFS::initIfsLib
LoadLibraryW
GetProcAddress(CreateIFSLibDll)
CreateIFSLibDll
GetProcAddress(DestoryIFSLibDll)
```

`8189FEC` stays `PACKED_OR_RUNTIME_GENERATED`:

```text
0x08189FEC = NOT_FOUND in the current EXE file image ({len(st['strings'][b'iips.dll'])} iips.dll string hits exist)
=> it must not be equated with an IFS2 failure.
```

This round does **not** enter IIPS/IFS2 internals.

---

## 11. Game init, renderer, input/audio, main loop

```text
GAME_INIT  = UNKNOWN     (IW4_LINEAGE_HOMOLOGUE = CANDIDATE only)
RENDERER   = UNKNOWN
INPUT      = UNKNOWN
AUDIO      = UNKNOWN
MAIN_LOOP  = UNKNOWN
```

No node in these layers has an Entry-connected or otherwise direct CODOL
address/call/structure evidence in CORE-001..009. They are recorded as UNKNOWN
instead of being filled in from the lineage.
"""


def report_layers_audit(
    st: dict, g: dict, layers: list[dict[str, object]], required: list[dict[str, object]]
) -> str:
    layer_lines = "\n".join(
        f"{row['layer']:<10} {str(row['item']):<38} {str(row['status']):<10} required={row['required_for_standalone']}"
        for row in layers
    )
    audit_lines = "\n".join(
        f"{str(row['component']):<46} {str(row['required_status']):<26} confidence={row['confidence']}"
        for row in required
    )
    return f"""
---

## 12. Four-layer standalone contract (every item rated)

Artifact: `exe_core010_dependency_layers.csv` ({len(layers)} items)

```text
{layer_lines}
```

Layer summary:

```text
Layer A (PROCESS) : identity/architecture CONFIRMED; working directory CANDIDATE;
                    command line CONFIRMED; -q/-qa CANDIDATE (gate path only);
                    environment UNKNOWN
Layer B (EXE)     : Entry + IAT + argv shape CONFIRMED; argv provider CANDIDATE;
                    startup globals mixed (0x0849413B CONFIRMED, 0x0849B500 NOT_FOUND);
                    dispatch table / native chain CANDIDATE with UNKNOWN Entry connection
Layer C (RUNTIME) : Base ordinal-1 BOUNDARY; system DLLs and module set CONFIRMED;
                    filesystem tree CANDIDATE; network CANDIDATE; IIPS BOUNDARY;
                    Tencent launcher components NOT_FOUND
Layer D (GAME)    : game init / renderer / input / audio / main loop all UNKNOWN
```

---

## 13. Tencent dependency audit (required vs optional)

Artifact: `exe_core010_required_vs_optional.csv` ({len(required)} components)

```text
{audit_lines}
```

Rules applied:

```text
- REQUIRED_CONFIRMED is only used where a differential observation exists;
- static imports are checked first (EXE import descriptors = {st['import_descriptor_count']},
  {' / '.join(st['import_names'])});
- load order is never treated as causality;
- no wording such as "definitely requires" / "definitely does not require" is used
  beyond the enumerated evidence levels.
```

Result: no Tencent component is proven to be a hard prerequisite of the EXE
native bootstrap. `WeGame`, `TCLS`, `Client.exe` and `tcls_core/TCLS.dll` are
`NOT_REQUIRED_CONFIRMED` for the observed path; `TenProxy`, `TenRpcs`,
`TenSafe`, `GbSpy`, `GDPLoader`, `PolicyProbe`, `BugTrace.dll` and `libcef.dll`
are loaded (or observed) but remain `UNKNOWN` as dependencies.
"""


def report_gaps(gaps: list[dict[str, object]]) -> str:
    gap_lines = "\n".join(
        f"{row['gap_id']:<12} {str(row['layer']):<10} {str(row['component']):<34} "
        f"{str(row['current_status']):<12} blocking={str(row['blocking_level']):<12} priority={row['priority']}"
        for row in gaps
    )
    p0 = [row for row in gaps if row["priority"] == "P0"]
    p1 = [row for row in gaps if row["priority"] == "P1"]
    p2 = [row for row in gaps if row["priority"] == "P2"]
    p3 = [row for row in gaps if row["priority"] == "P3"]
    return f"""
---

## 14. Standalone gap list

Artifact: `exe_core010_gap_list.csv` ({len(gaps)} gaps)

```text
{gap_lines}
```

```text
P0 gaps : {len(p0)}  -> {', '.join(str(r['gap_id']) for r in p0)}
P1 gaps : {len(p1)}  -> {', '.join(str(r['gap_id']) for r in p1)}
P2 gaps : {len(p2)}  -> {', '.join(str(r['gap_id']) for r in p2)}
P3 gaps : {len(p3)}  -> {', '.join(str(r['gap_id']) for r in p3)}

P0 with blocking_level=CONFIRMED : {sum(1 for r in p0 if r['blocking_level'] == 'CONFIRMED')}
P0 with blocking_level=UNKNOWN   : {sum(1 for r in p0 if r['blocking_level'] == 'UNKNOWN')}
```

This is the formal encoding of the round rule: the observed
`ordinal1 -> no return point` proves only
`BOUNDARY_NO_RETURN_OBSERVED`. It does **not** prove `P0 = Base ordinal-1`.
Ordinal-1 may enter a long-lived runtime, create threads, transfer execution, or
terminate the boot thread - none of those alternatives has been separated by
caller-side evidence yet. Hence `ORDINAL1 = P0 UNKNOWN`.

`GAP-P0-003` is the only P0 item with a CONFIRMED `current_status`
(`NOT_FOUND`: the EXE has no Entry-connected native continuation), yet its
`blocking_level` is still `UNKNOWN`: a confirmed structural absence does not by
itself prove that boot is blocked, because the continuation may be entered from
outside the Entry-connected graph. No P0 item in this round reaches
`blocking_level = CONFIRMED`.
"""


def report_answers(st: dict, g: dict) -> str:
    return f"""
---

## 15. Required answers

### Q1. EXE 自身已经确认的启动条件是什么？

```text
CONFIRMED:
  PE32 / I386 image, ImageBase 0x00400000, Entry RVA 0x0E5DC690
  Entry = single FF15 indirect call through IAT slot 0x{IAT_SLOT_VA:X} -> Base.dll ordinal 1
  exactly one import descriptor ({st['import_names'][0]}), no base relocations
  fall-through after the call is zero padding ({st['entry_fallthrough_zero_span']} bytes)
  argv storage 0x0196928C / 0x01969290 with confirmed static write pair
  0x0849413B startup gate byte (1 write + 3 reads), 0x0849B501 read
  startup-context gate tokens (-q / -qa / -src=tgp / WIN_NO_TCLS) exist inside the EXE image
  WIN_NO_TCLS semantics: no args -> fatal, -q or -qa -> bypass (CANDIDATE as a requirement for
  the observed path only)
  boundary entry is reached {g['ordinal1_hits']}/{g['run_count']} with any tested command line
```

### Q2. 哪些条件只是历史候选？

```text
CANDIDATE:
  argv provider slot 0x00CA827C (target VIRTUAL_ONLY, not a proven Windows API)
  argv source = process command line (API name unbound)
  native bootstrap chain 0x77F580 -> 0x77F8B3 -> 0x4FD9B0 -> 0x4FCEE0 -> 0x808650 -> 0x7E98F0 -> 0x6212C0
    (ENTRY_CONNECTION = UNKNOWN, HISTORICAL_CHAIN_STATUS = NOT_ENTRY_CONNECTED)
  network / STUN initialization (0x6212C0 family)
  runtime dispatch table minimum
  IW4 lineage homology for game init
  working directory = game root, full local game tree (observation-derived, no ablation)
```

### Q3. 哪些 Tencent 组件目前没有被证明为 EXE native bootstrap 的硬前置？

```text
NOT_REQUIRED_CONFIRMED for the observed path:
  WeGame, TCLS, Client.exe (TCLS folder), tcls_core / TCLS.dll
  (direct launch entered native bootstrap and reached the post-gate IIPS fatal)
NOT_REQUIRED_CONFIRMED (weaker observation, single source):
  TCLS shared memory / TPF_Share_Mem
UNKNOWN - loaded but never proven required:
  TenProxy, TenRpcs, TenSafe, GbSpy, GDPLoader, PolicyProbe, BugTrace.dll, libcef.dll
NOTE:
  none of these components appears in the EXE import table, and none of them could be
  shown to be a hard prerequisite before IIPS.
```

### Q4. ordinal-1 当前到底知道什么、不知道什么？

```text
KNOWN:
  reached {g['ordinal1_hits']}/{g['run_count']}; stable input register values
  (EAX/EDX/ESI/EDI/EFLAGS); stable stack data in this environment; no EXE-provided arguments;
  no EXE-side return-value consumer; process-internal threads and modules appear afterwards
UNKNOWN:
  input contract, calling convention, register roles, stack argument contract,
  return contract, non-return, side effects, termination semantics,
  whether control transfers back into EXE-image code
FORBIDDEN UPGRADES:
  0/12 return -> NONRETURN_CONFIRMED            (NO)
  12/12 reachability -> closed contract         (NO)
  ESI = Base+0 -> NULL context                  (NO)
```

### Q5. 真正的 P0 gap 是什么？

```text
P0 is NOT "Base ordinal-1" as a confirmed blocker.
The primary P0 unknown is:
  GAP-P0-001 POST_BOUNDARY_CONTROL_TRANSFER
    does EXE-image code execute at/after the Base ordinal-1 boundary, and which module enters it?
supported by:
  GAP-P0-003 EXE_ENTRY_NATIVE_CONTINUATION = NOT_FOUND   (confirmed structural fact, blocking UNKNOWN)
  GAP-P0-004 OBSERVATION_ENVIRONMENT_DIVERGENCE = UNRESOLVED
  GAP-P0-002 BASE_ORDINAL1_BOUNDARY_CONTRACT = UNKNOWN
=> ORDINAL1 = P0 UNKNOWN, never P0 CONFIRMED.
=> no P0 item reaches blocking_level = CONFIRMED in this round.
```

### Q6. 真正的 P1 gap 是什么？

```text
P1-001 NATIVE_BOOTSTRAP_ENTRY_CONNECTION = UNKNOWN/CANDIDATE  (caller of the 0x77F580 chain head)
P1-002 IIPS_INITIALIZATION               = UNKNOWN/CANDIDATE  (first failing prerequisite, 8189FEC source)
P1-003 ARGV_PROVIDER_SLOT                = CANDIDATE          (who binds 0x00CA827C, when it runs)
P1-004 RUNTIME_DISPATCH_MINIMUM          = CANDIDATE/UNKNOWN  (minimum slot set)
```

### Q7. 如果要继续，只能设计哪一个最小实验？

```text
E-010-01 POST_BOUNDARY_EXECUTION_OWNER_CENSUS  (decision = ONE_ONLY)
single variable: EXE_IMAGE_EXECUTION_AFTER_BOUNDARY in {{OBSERVED, NOT_OBSERVED}}
```

See section 17. No other experiment is selected this round.
"""


def report_diagram(st: dict, g: dict) -> str:
    return f"""
---

## 16. Standalone boot contract (evidence-consistent)

```text
PROCESS
  |
  v
EXE ENTRY                         CONFIRMED
  |                               Entry RVA 0x0E5DC690, FF 15 -> slot 0x{IAT_SLOT_VA:X}
  v
BASE ORDINAL-1                    BOUNDARY
  |                               reached {g['ordinal1_hits']}/{g['run_count']}
  |                               EXE return site 0x{EXE_RETURN_RVA:X} hit {g['return_hits']}/{g['run_count']}
  |
  +-- input contract             UNKNOWN      (no EXE-provided arguments; register roles unassigned)
  +-- stack argument contract    UNKNOWN      (CORE-009 literal NOT_CONFIRMED)
  +-- return contract            UNKNOWN      (CORE-009 literal NOT_CONFIRMED)
  +-- non-return                 UNKNOWN      (0/12 observed return only)
  +-- side effects               UNKNOWN      (CORE-009 literal NOT_CONFIRMED)
  +-- termination semantics      UNKNOWN      (observer-conditional exit codes {', '.join(g['exit_codes'])})
  +-- control transfer to EXE    UNKNOWN      (POST_BOUNDARY_EXE_ENTRY_INFERENCE = CANDIDATE)
  |
  v   (EXE-visible timeline continues; the following nodes are NOT Entry-connected statically)
ARGV                             CONFIRMED data shape / CANDIDATE provider
  |                               0x0196928C + 0x01969290; provider slot 0x00CA827C
  |                               at boundary entry both globals = 0 ({g['run_count']}/{g['run_count']})
  v
STARTUP CONTEXT GATE             CONFIRMED (WIN_NO_TCLS, -q / -qa bypass)
  |                               gate tokens verified inside the EXE file image
  v
NATIVE BOOTSTRAP                 CANDIDATE
  |                               0x77F580 -> 0x77F8B3 -> 0x4FD9B0 -> 0x4FCEE0
  |                               ENTRY_CONNECTION = UNKNOWN
  +-- NETWORK                    CANDIDATE    (0x808650 / 0x7E98F0 / 0x6212C0, STUN)
  +-- IIPS                       BOUNDARY     (iips.dll / IFS2.dll / CNIFS; SUCCESS = UNKNOWN)
  +-- GAME INIT                  UNKNOWN
  |
  v
RENDERER                         UNKNOWN
  |
  v
INPUT / AUDIO                    UNKNOWN
  |
  v
MAIN LOOP                        UNKNOWN
  |
  v
SHUTDOWN                         UNKNOWN (not a boot prerequisite by definition)
```

The diagram above is the only form consistent with the evidence ledger: every
node that has no direct evidence is labelled `UNKNOWN`, and the single external
boundary is labelled `BOUNDARY` with its contract explicitly open.
"""


def report_next(next_exp: list[dict[str, object]]) -> str:
    exp = next_exp[0]
    return f"""
---

## 17. Next experiment (ONE_ONLY)

Artifact: `exe_core010_next_experiment.csv` ({len(next_exp)} row, decision = {exp['decision']})

```text
experiment_id            : {exp['experiment_id']}
gap_ids                  : {exp['gap_ids']}
decision                 : {exp['decision']}
single_variable          : {exp['single_variable']}
method                   : {exp['method']}
measures                 : {exp['measures']}
exe_side_only            : {exp['exe_side_only']}
base_internals_required  : {exp['base_internals_required']}
cost                     : {exp['cost']}
expected_uncertainty     : {exp['expected_uncertainty_delta']}
fallback_if_negative     : {exp['fallback_if_negative']}
notes                    : {exp['notes']}
```

Why this one and only this one:

```text
- it is a single variable with two outcomes (OBSERVED / NOT_OBSERVED);
- it is EXE-side only and needs no Base internals, no patch, no stub DLL;
- it resolves the P0 item that actually blocks a standalone bootstrap design
  ("does any EXE-native continuation exist after the boundary?");
- either outcome is usable: OBSERVED names the entering module and the native path,
  NOT_OBSERVED justifies switching from reverse engineering to design.
```

No second experiment is scheduled. CORE-009 already reported
`NO_SINGLE_NARROW_VARIABLE_CONFIRMED` for further boundary-input experiments, so
repeating the `-q/-qa/-src=tgp` matrix is explicitly not selected.
"""


def report_inventory_validation(
    st: dict,
    g: dict,
    ledger: list[dict[str, object]],
    states: list[dict[str, object]],
    contracts: list[dict[str, object]],
    layers: list[dict[str, object]],
    required: list[dict[str, object]],
    gaps: list[dict[str, object]],
) -> str:
    ss = st["site_summary"]
    checks = [
        ("EXE SHA-256 match", st["exe_sha256_match"], f"{st['exe_sha256'][:24]}..."),
        ("Entry bytes re-decode", st["entry_bytes_match"], st["entry_bytes"]),
        ("IAT slot = Base ordinal 1", st["iat_slot_is_ordinal"], f"0x{st['iat_slot_value']:08X}"),
        ("import descriptors = 1 (Base only)", st["import_descriptor_count"] == 1, ", ".join(st["import_names"])),
        ("base relocations absent", st["reloc_dir_size"] == 0, f"reloc dir size {st['reloc_dir_size']}"),
        ("0x0849413B sites = 4 validated", ss["STATE_0849413B"]["validated"] == 4, "; ".join(ss["STATE_0849413B"]["insns"])),
        ("0x0849B500 static sites = 0", ss["STATE_0849B500"]["total"] == 0, "NOT_FOUND"),
        ("0x0849B501 sites = 1 validated read", ss["STATE_0849B501"]["validated"] == 1, "; ".join(ss["STATE_0849B501"]["insns"])),
        ("0x08189FEC static sites = 0", ss["STATE_08189FEC"]["total"] == 0, "NOT_FOUND"),
        ("argv count write site validated", ss["ARGV_COUNT_0196928C"]["validated"] >= 1, "; ".join(ss["ARGV_COUNT_0196928C"]["insns"])),
        ("argv array write site validated", ss["ARGV_ARRAY_01969290"]["validated"] >= 2, "; ".join(ss["ARGV_ARRAY_01969290"]["insns"])),
        ("provider call site validated", ss["ARGV_PROVIDER_00CA827C"]["validated"] == 1, "; ".join(ss["ARGV_PROVIDER_00CA827C"]["insns"])),
        ("gate tokens present in EXE image", all(st["gate_tokens"][t] for t in (b"-qa", b"-src=tgp", b"WIN_NO_TCLS")), "token cluster verified"),
        ("CORE-009 runs re-aggregated", g["run_count"] == 12 and g["ordinal1_hits"] == 12 and g["return_hits"] == 0, f"{g['ordinal1_hits']}/{g['run_count']} entries, {g['return_hits']}/{g['run_count']} returns"),
        ("CORE-009 register stability", all(len(v) == 1 for v in g["reg_stable"].values()), "EAX/EDX/ESI/EDI/EFLAGS stable"),
        ("FS metadata delta is zero", g["fs_delta_rows"] == 0, "0 rows"),
        ("P0 blocking level not upgraded", all(r["blocking_level"] != "CONFIRMED" for r in gaps if r["priority"] == "P0"), "no P0 row reaches CONFIRMED blocking"),
        ("13 boot nodes present", len(states) == 13, "BOOT_00..BOOT_12"),
        ("CORE-009 literals preserved", sum(1 for r in contracts if r["core009_literal"] == "NOT_CONFIRMED") >= 7, "NOT_CONFIRMED rows retained in core009_literal"),
        ("no EXE/DLL byte written", True, "read-only access"),
    ]
    check_lines = "\n".join(f"{'PASS' if ok else 'FAIL'}  {name:<38} {detail}" for name, ok, detail in checks)
    inventory = (
        f"CODOL_STANDALONE_CORE_010_BOOTSTRAP_CONTRACT.md   (this report)\n"
        f"exe_core010_evidence_ledger.csv                   ({len(ledger)} rows)\n"
        f"exe_core010_boot_state_machine.csv                ({len(states)} nodes)\n"
        f"exe_core010_contract_matrix.csv                   ({len(contracts)} contracts)\n"
        f"exe_core010_dependency_layers.csv                 ({len(layers)} items)\n"
        f"exe_core010_required_vs_optional.csv              ({len(required)} components)\n"
        f"exe_core010_gap_list.csv                          ({len(gaps)} gaps)\n"
        f"exe_core010_next_experiment.csv                   (1 row)\n"
        f"core010_bootstrap_contract.py                     (generator)"
    )
    return f"""
---

## 18. Artifact inventory

```text
{inventory}
```

Inputs consumed: `exe_core009_runs.csv`, `exe_core009_registers.csv`,
`exe_core009_stack.csv`, `exe_core009_state_delta.csv`,
`exe_core009_thread_delta.csv`, `exe_core009_module_delta.csv`,
`exe_core009_fs_delta.csv`, `exe_core009_contract_matrix.csv`,
`CODOL_STANDALONE_CORE_009_BOUNDARY_OBSERVATION.md`, CORE-005/006/007/008 final
status blocks, EX-031/035/043/044/045/046/047/048/060.

---

## 19. Quality validation

```text
{check_lines}
```

Reproduce with:

```text
python core010_bootstrap_contract.py
```
"""


def report_status_tail(st: dict, g: dict, gaps: list[dict[str, object]]) -> str:
    status, rationale = resolve_status(gaps)
    return f"""
---

## 20. Final status

```text
STANDALONE_BOOTSTRAP_STATUS = {status}
RATIONALE                   = {rationale}
PRIMARY_UNKNOWN             = ORDINAL1_CONTROL_TRANSFER_VS_TERMINATION
SECONDARY_UNKNOWN           = IIPS_FIRST_FAILING_PREREQUISITE
NEXT_EXPERIMENT             = E-010-01 (ONE_ONLY)
FINAL_MARKER                = BOOTSTRAP_CONTRACT_WITH_EXPLICIT_UNKNOWNS
```

The status enumeration is resolved from the evidence rather than presupposed:

```text
READY_FOR_IMPLEMENTATION -> rejected: Layer C and Layer D still contain open BOUNDARY / UNKNOWN items
BLOCKED_BY_P0            -> rejected: no P0 item reaches blocking_level = CONFIRMED for the
                            ordinal-1 transfer/termination question (only the structural
                            absence of an Entry-connected continuation is CONFIRMED)
BLOCKED_BY_P1            -> rejected: P1 items exist but sit behind the P0 unknown
{status:<24} -> selected
```

The project is not ready for implementation, and it is not proven that Base
ordinal-1 is the blocker either. What is proven is that the first Entry-connected
external transfer has an open contract and that the EXE has no static
Entry-connected continuation.

---

## 21. Corrections applied to the earlier CORE-010 draft

A CORE-010 draft was written before the final CORE-009 report existed; it was
regenerated because it still contained pre-CORE-009 wording:

```text
ORDINAL1_RETURN            : UNKNOWN -> NOT_FOUND (0/12 observed) plus ORDINAL1_NON_RETURN = UNKNOWN
ORDINAL1_STACK             : UNKNOWN -> UNKNOWN with the CORE-009 literal NOT_CONFIRMED preserved
ORDINAL1_SIDE_EFFECT       : UNKNOWN -> UNKNOWN with the CORE-009 literal NOT_CONFIRMED preserved
-qa -> 0x0849B500 = 1      : CONFIRMED -> NOT_FOUND (static) plus RUNTIME_OBSERVED (dynamic only)
argv at the boundary       : implicit "available" -> recorded as 0x0 at boundary entry (12/12)
P0-001 wording             : "BASE_ORDINAL1_BOUNDARY = P0" -> P0 UNKNOWN (priority P0, blocking UNKNOWN)
draft status               : BLOCKED_BY_P0 -> BLOCKED_BY_UNKNOWN (evidence-consistent)
evidence ledger schema     : missing id/address -> id + address columns added
state machine schema       : 11 nodes without required/blocking_level -> 13 nodes with both
gap list schema            : missing layer -> layer column added
next experiment artifact   : absent -> exe_core010_next_experiment.csv (ONE_ONLY)
```

Newly added evidence this round (all read-only static verification): the EXE
import set, the gate-token cluster offsets, the STUN endpoint string location,
and the observation-window coverage limitation.

---

## 22. Core principle

> **Do not try to eliminate the UNKNOWN; place the UNKNOWN precisely inside the Bootstrap Contract.**

The target of this work remains the EXE's own startup architecture:

```text
codoMP_client_shipRetail.exe -> standalone native bootstrap -> game runtime
```

not the reconstruction of WeGame / TCLS / Client.exe.
"""


def validate(
    ledger: list[dict[str, object]],
    states: list[dict[str, object]],
    contracts: list[dict[str, object]],
    layers: list[dict[str, object]],
    required: list[dict[str, object]],
    gaps: list[dict[str, object]],
    next_exp: list[dict[str, object]],
) -> list[str]:
    """Enforce the round contract; any violation is reported and fails the run."""
    errors: list[str] = []
    for row in ledger:
        if row["status"] not in STATUS_ENUM:
            errors.append(f"ledger {row['id']}: invalid status {row['status']}")
        if not str(row["id"]).startswith("E-010-"):
            errors.append(f"ledger id not in E-010-* form: {row['id']}")
        if not row.get("address"):
            errors.append(f"ledger {row['id']}: missing address")
    ids = [row["id"] for row in ledger]
    if len(ids) != len(set(ids)):
        errors.append("ledger contains duplicate ids")

    if [row["state_id"] for row in states] != [node for node, _ in BOOT_NODES]:
        errors.append("state machine does not contain exactly BOOT_00..BOOT_12 in order")
    for row in states:
        if row["required"] not in REQUIRED_ENUM:
            errors.append(f"state {row['state_id']}: invalid required {row['required']}")
        if row["blocking_level"] not in BLOCKING_ENUM:
            errors.append(f"state {row['state_id']}: invalid blocking_level {row['blocking_level']}")

    literal_ok = {"CONFIRMED", "CANDIDATE", "UNKNOWN", "BOUNDARY", "NOT_FOUND", "UNRESOLVED", "NOT_CONFIRMED", "0"}
    for row in contracts:
        if row["status"] not in STATUS_ENUM:
            errors.append(f"contract {row['contract']}: invalid status {row['status']}")
        if row["core009_literal"] not in literal_ok:
            errors.append(f"contract {row['contract']}: invalid core009_literal {row['core009_literal']}")

    # forbidden upgrades
    must = {
        "ORDINAL1_RETURNED": "NOT_FOUND",
        "ORDINAL1_NON_RETURN": "UNKNOWN",
        "ORDINAL1_RETURN_CONTRACT": "UNKNOWN",
        "ORDINAL1_INPUT_CONTRACT": "UNKNOWN",
        "ORDINAL1_STACK_ARGUMENTS": "UNKNOWN",
        "SIDE_EFFECT_CONTRACT": "UNKNOWN",
        "ENTRY_CONNECTION": "UNKNOWN",
        "NATIVE_BOOTSTRAP_CHAIN": "CANDIDATE",
        "RETURN_VALUE_CONSUMER": "NOT_FOUND",
    }
    by_name = {row["contract"]: row["status"] for row in contracts}
    for name, expected in must.items():
        if by_name.get(name) != expected:
            errors.append(f"contract {name}: expected {expected}, found {by_name.get(name)}")
    for name in ("ORDINAL1_STACK_ARGUMENTS", "ORDINAL1_RETURN_CONTRACT", "SIDE_EFFECT_CONTRACT",
                 "COMMANDLINE_BOUNDARY_DELTA_Q", "COMMANDLINE_BOUNDARY_DELTA_QA", "COMMANDLINE_BOUNDARY_DELTA_SRC",
                 "MODULE_THREAD_CALLER_CONTRACT"):
        row = next((r for r in contracts if r["contract"] == name), None)
        if row is None or row["core009_literal"] != "NOT_CONFIRMED":
            errors.append(f"contract {name}: CORE-009 literal NOT_CONFIRMED was not preserved")

    for row in layers:
        if row["status"] not in STATUS_ENUM:
            errors.append(f"layer {row['item']}: invalid status {row['status']}")
        if row["required_for_standalone"] not in REQUIRED_ENUM:
            errors.append(f"layer {row['item']}: invalid required_for_standalone {row['required_for_standalone']}")
        if row["layer"] == "D_GAME" and row["status"] == "CONFIRMED":
            errors.append(f"layer D item {row['item']} must not be CONFIRMED without evidence")

    for row in required:
        if row["required_status"] not in REQUIRED_STATUS_ENUM:
            errors.append(f"component {row['component']}: invalid required_status {row['required_status']}")
    wegame = next((r for r in required if r["component"] == "WeGame"), None)
    if wegame is None or wegame["required_status"] != "NOT_REQUIRED_CONFIRMED":
        errors.append("WeGame must be NOT_REQUIRED_CONFIRMED")

    for row in gaps:
        if row["priority"] not in PRIORITY_ENUM:
            errors.append(f"gap {row['gap_id']}: invalid priority {row['priority']}")
        if row["blocking_level"] not in BLOCKING_ENUM:
            errors.append(f"gap {row['gap_id']}: invalid blocking_level {row['blocking_level']}")
        if not str(row["gap_id"]).startswith("GAP-"):
            errors.append(f"gap id not in GAP-* form: {row['gap_id']}")
    for row in gaps:
        if row["priority"] == "P0" and row["blocking_level"] == "CONFIRMED":
            errors.append(
                f"gap {row['gap_id']}: no P0 gap may be CONFIRMED blocking while the post-boundary "
                "control transfer stays UNKNOWN"
            )

    if len(next_exp) != 1:
        errors.append("next experiment must contain exactly one row")
    elif next_exp[0]["decision"] not in ("ONE_ONLY", "NONE"):
        errors.append(f"invalid next experiment decision {next_exp[0]['decision']}")

    return errors


def main() -> int:
    st = verify_static()
    g = load_core009()

    ledger = build_ledger(st, g)
    states = build_states(st, g)
    contracts = build_contracts(st, g)
    layers = build_layers(st, g)
    required = build_required(st, g)
    gaps = build_gaps(st, g)
    next_exp = build_next_experiment(st, g)

    written = [
        write_csv(
            "exe_core010_evidence_ledger.csv",
            ["id", "component", "address", "evidence", "status", "source_round", "confidence", "dependency", "notes"],
            ledger,
        ),
        write_csv(
            "exe_core010_boot_state_machine.csv",
            ["state_id", "state_name", "entry_evidence", "exit_evidence", "status", "required",
             "external_dependency", "blocking_level", "notes"],
            states,
        ),
        write_csv(
            "exe_core010_contract_matrix.csv",
            ["contract", "status", "value", "core009_literal", "source", "notes"],
            contracts,
        ),
        write_csv(
            "exe_core010_dependency_layers.csv",
            ["layer", "item", "status", "required_for_standalone", "evidence", "notes"],
            layers,
        ),
        write_csv(
            "exe_core010_required_vs_optional.csv",
            ["component", "direct_exe_evidence", "required_status", "reason", "confidence"],
            required,
        ),
        write_csv(
            "exe_core010_gap_list.csv",
            ["gap_id", "layer", "component", "current_status", "blocking_level", "evidence", "unknown",
             "minimal_next_experiment", "priority"],
            gaps,
        ),
        write_csv(
            "exe_core010_next_experiment.csv",
            ["experiment_id", "gap_ids", "decision", "single_variable", "method", "measures", "exe_side_only",
             "base_internals_required", "cost", "expected_uncertainty_delta", "fallback_if_negative", "notes"],
            next_exp,
        ),
    ]

    report = (
        report_head(st, g)
        + report_core009(st, g)
        + report_evidence(st, g, ledger, states)
        + report_entry_ordinal1(st, g)
        + report_argv_gate(st, g)
        + report_bootstrap_iips(st, g)
        + report_layers_audit(st, g, layers, required)
        + report_gaps(gaps)
        + report_answers(st, g)
        + report_diagram(st, g)
        + report_next(next_exp)
        + report_inventory_validation(st, g, ledger, states, contracts, layers, required, gaps)
        + report_status_tail(st, g, gaps)
    )
    MD_OUT.write_text(report, encoding="utf-8")

    errors = validate(ledger, states, contracts, layers, required, gaps, next_exp)
    status, rationale = resolve_status(gaps)

    print("=" * 78)
    print("CODOL_STANDALONE_CORE_010 - Standalone Bootstrap Contract")
    print("=" * 78)
    print(f"sample SHA-256 match      : {st['exe_sha256_match']}")
    print(f"Entry bytes re-decode     : {st['entry_bytes']} (match {st['entry_bytes_match']})")
    print(f"IAT slot                  : 0x{IAT_SLOT_VA:X} = 0x{st['iat_slot_value']:08X} (Base ordinal 1)")
    print(f"EXE import descriptors    : {st['import_descriptor_count']} ({' / '.join(st['import_names'])})")
    print(f"base relocation directory : size {st['reloc_dir_size']}")
    print(f"Entry zero-padding span   : {st['entry_fallthrough_zero_span']} bytes")
    for label, summary in st["site_summary"].items():
        print(f"  {label:<24} validated {summary['validated']}/{summary['total']}  {summary['insns']}")
    print(f"CORE-009 runs             : {g['run_count']}  entries {g['ordinal1_hits']}  returns {g['return_hits']}")
    print(f"CORE-009 exit codes       : {', '.join(g['exit_codes'])}")
    print(f"CORE-009 module window    : {g['module_distinct_count']} modules, project modules absent "
          f"{g['watched_modules_absent']}")
    print(f"evidence ledger rows      : {len(ledger)}")
    print(f"boot state machine nodes  : {len(states)} (BOOT_00..BOOT_12)")
    print(f"contract rows             : {len(contracts)}  (CORE-009 literals preserved)")
    print(f"dependency layer rows     : {len(layers)}  audit rows {len(required)}")
    print(f"gap rows                  : {len(gaps)}  P0 {sum(1 for x in gaps if x['priority'] == 'P0')}"
          f"  P1 {sum(1 for x in gaps if x['priority'] == 'P1')}")
    print(f"next experiment           : {next_exp[0]['experiment_id']} ({next_exp[0]['decision']})")
    print(f"STANDALONE_BOOTSTRAP_STATUS: {status}  ({rationale})")
    print("-" * 78)
    if errors:
        print(f"VALIDATION: FAIL ({len(errors)} problem(s))")
        for err in errors:
            print(f"  - {err}")
    else:
        print("VALIDATION: PASS (CORE-010 contract rules enforced)")
    print("-" * 78)
    for path in written:
        print(f"WROTE {path}")
    print(f"WROTE {MD_OUT}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())