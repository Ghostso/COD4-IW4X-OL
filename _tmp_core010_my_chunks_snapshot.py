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


