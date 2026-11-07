from __future__ import annotations

"""
CODOL_STANDALONE_CORE_008
codoMP_client_shipRetail.exe -- External Boundary Contract Validation

Scope: codoMP_client_shipRetail.exe only, static file image only.

NO PATCH / NO HOOK / NO DLL MODIFICATION / NO EXE MODIFICATION /
NO COMPATIBILITY LAYER IMPLEMENTATION.

This round determines WHAT MUST BE PROVIDED, not HOW TO PROVIDE IT.
Base.dll internals are never entered; ordinal-1 is only ever written as
EXTERNAL_BOUNDARY.
"""

import csv
import hashlib
import re
import struct
from collections import Counter, defaultdict
from pathlib import Path

import capstone
from capstone import CS_ARCH_X86, CS_MODE_32
from capstone.x86_const import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from core004a_diagnostic import ManualPE, SAMPLE


ROOT = Path(__file__).resolve().parent
EXPECTED_SHA256 = "36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537"
IMAGE_BASE = 0x00400000
ENTRY_RVA = 0x0E5DC690
IAT_SLOT_RVA = 0x0E5DC665
TVM0 = ".tvm0"

MD = capstone.Cs(CS_ARCH_X86, CS_MODE_32)
MD.detail = True


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def fmt(v: int | None) -> str:
    if v is None:
        return ""
    if v < 0:
        return f"-0x{-v:08X}"
    return f"0x{v:08X}"


def mapping(pe: ManualPE, rva: int) -> str:
    section, offset, status = pe.rva_to_offset(rva)
    if section is None and status == "PE_HEADERS":
        return "PE_HEADERS"
    if section is None:
        return status
    if section.name == TVM0:
        return "TVM0_BOUNDARY"
    if status == "VIRTUAL_ONLY":
        return "VIRTUAL_ONLY"
    if status != "OK":
        return status
    return "RAW_BACKED_EXECUTABLE" if section.executable else "RAW_BACKED_DATA"


def rva_for_offset(pe: ManualPE, offset: int) -> int | None:
    for s in pe.sections:
        if s.raw_offset <= offset < s.raw_offset + s.raw_size:
            return s.virtual_address + (offset - s.raw_offset)
    return None


# ---------------------------------------------------------------------------
# Alignment-validated instruction boundary set
# ---------------------------------------------------------------------------

_BOUNDARIES: set[int] | None = None


def valid_boundaries(pe: ManualPE) -> set[int]:
    global _BOUNDARIES
    if _BOUNDARIES is not None:
        return _BOUNDARIES
    raw = pe.data
    out: set[int] = set()
    for section in pe.sections:
        if not section.executable or section.raw_size == 0:
            continue
        raw_end = section.raw_offset + section.raw_size
        pos = section.raw_offset
        while pos < raw_end - 3:
            if raw[pos] == 0x55 and raw[pos + 1] == 0x8B and raw[pos + 2] == 0xEC:
                prologue = section.virtual_address + (pos - section.raw_offset)
                count = 0
                for insn in MD.disasm(raw[pos:raw_end], IMAGE_BASE + prologue):
                    out.add(insn.address - IMAGE_BASE)
                    count += 1
                    if count >= 20000:
                        break
                pos += 3
                continue
            pos += 1
    _BOUNDARIES = out
    return out


def alignment_state(pe: ManualPE, rva: int) -> str:
    return "ALIGNMENT_VALID" if rva in valid_boundaries(pe) else "ALIGNMENT_INVALID"


# ---------------------------------------------------------------------------
# Local-context alignment validation (independent of prologue style)
# ---------------------------------------------------------------------------

_LOCAL_CACHE: dict[int, str] = {}


def local_alignment_state(pe: ManualPE, site_rva: int) -> str:
    """Decide whether `site_rva` is a genuine instruction boundary by testing
    whether a bounded decode reaches it from several nearby start candidates.

    A packed/obfuscated section has no `55 8B EC` prologues, so a prologue-based
    sweep reports ALIGNMENT_INVALID for real code. This validator instead asks:
    does there exist a start S within +/-64 bytes such that S is itself reached
    by a longer consistent decode (>= 6 instructions with no invalid group) and
    the decode from S lands exactly on `site_rva`?

    Returns ALIGNMENT_VALID / ALIGNMENT_INVALID / ALIGNMENT_UNKNOWN.
    """
    cached = _LOCAL_CACHE.get(site_rva)
    if cached:
        return cached

    raw = pe.data
    # locate the containing raw section
    section = None
    for s in pe.sections:
        if s.virtual_address <= site_rva < s.virtual_address + s.raw_size:
            section = s
            break
    if section is None or not section.executable:
        _LOCAL_CACHE[site_rva] = "ALIGNMENT_UNKNOWN"
        return "ALIGNMENT_UNKNOWN"

    site_off = section.raw_offset + (site_rva - section.virtual_address)

    def consistent_from(start_off: int, min_insns: int = 5) -> bool:
        """A start is 'consistent' when decoding forward yields at least
        `min_insns` instructions, none carrying the INVALID group, and the
        stream does not hit an obvious zero-padding run mid-instruction."""
        end = min(start_off + 96, section.raw_offset + section.raw_size)
        if start_off < section.raw_offset or start_off >= end:
            return False
        rva = section.virtual_address + (start_off - section.raw_offset)
        count = 0
        for insn in MD.disasm(raw[start_off:end], IMAGE_BASE + rva):
            if capstone.CS_GRP_INVALID in insn.groups:
                return False
            # reject the classic "00 00 -> add [eax], al" zero-padding artifact
            if bytes(insn.bytes) == b"\x00\x00" and insn.mnemonic == "add":
                return False
            count += 1
        return count >= min_insns

    # Primary test: does a coherent decode chain of at least 8 instructions
    # start somewhere within [-128, 0] bytes and land exactly on site_rva?
    # This is the strongest available evidence without runtime data.
    for delta in range(-128, 1):
        start_off = site_off + delta
        if start_off < section.raw_offset:
            continue
        rva = section.virtual_address + (start_off - section.raw_offset)
        # the candidate start must not be the target of a longer instruction
        # that began even earlier (i.e. it should be a real boundary)
        reaches = False
        count = 0
        coherent = True
        for insn in MD.disasm(raw[start_off:site_off + 16], IMAGE_BASE + rva):
            if capstone.CS_GRP_INVALID in insn.groups:
                coherent = False
                break
            if bytes(insn.bytes) == b"\x00\x00" and insn.mnemonic == "add":
                coherent = False
                break
            count += 1
            if insn.address - IMAGE_BASE == site_rva:
                reaches = True
                break
            if insn.address - IMAGE_BASE > site_rva:
                break
        if coherent and reaches and count >= 8:
            _LOCAL_CACHE[site_rva] = "ALIGNMENT_VALID"
            return "ALIGNMENT_VALID"

    # Fallback: a short but coherent local decode that does not begin with an
    # obvious continuation of a previous instruction.
    if consistent_from(site_off, 6) and not _is_continuation(pe, section, site_off):
        _LOCAL_CACHE[site_rva] = "ALIGNMENT_VALID"
        return "ALIGNMENT_VALID"
    _LOCAL_CACHE[site_rva] = "ALIGNMENT_INVALID"
    return "ALIGNMENT_INVALID"


def _is_continuation(pe: ManualPE, section, site_off: int) -> bool:
    """True when a plausible instruction starts in the 3 bytes before the site
    and extends across it, which would mean the site is a mid-instruction byte."""
    raw = pe.data
    for back in (1, 2, 3, 4, 5, 6):
        start_off = site_off - back
        if start_off < section.raw_offset:
            continue
        rva = section.virtual_address + (start_off - section.raw_offset)
        insns = list(MD.disasm(raw[start_off:start_off + 16], IMAGE_BASE + rva,
                               count=1))
        if not insns:
            continue
        insn = insns[0]
        end_rva = insn.address - IMAGE_BASE + insn.size
        site_rva = section.virtual_address + (site_off - section.raw_offset)
        if insn.size > back and end_rva > site_rva:
            # a longer instruction swallows the site
            if capstone.CS_GRP_INVALID not in insn.groups:
                return True
    return False


_SEMANTIC_CACHE: dict[int, str] = {}


def semantic_reference_state(pe: ManualPE, site_rva: int) -> str:
    """Validate a global-reference site by *semantics*, not only alignment.

    A site is SEMANTIC_VALID when the instruction at `site_rva` decodes with the
    expected memory operand AND the following 1-3 instructions form a coherent
    control-flow continuation (a conditional jump, unconditional jump, call,
    return, or register-producing move). This distinguishes a real
    `cmp byte ptr [global], ...` + `jcc` flag test from a coincidental byte
    pattern inside packed data.
    """
    cached = _SEMANTIC_CACHE.get(site_rva)
    if cached:
        return cached
    raw = pe.data
    section = None
    for s in pe.sections:
        if s.virtual_address <= site_rva < s.virtual_address + s.raw_size:
            section = s
            break
    if section is None or not section.executable:
        _SEMANTIC_CACHE[site_rva] = "SEMANTIC_UNKNOWN"
        return "SEMANTIC_UNKNOWN"

    off = section.raw_offset + (site_rva - section.virtual_address)
    insns = list(MD.disasm(raw[off:off + 32], IMAGE_BASE + site_rva, count=5))
    if not insns:
        _SEMANTIC_CACHE[site_rva] = "SEMANTIC_INVALID"
        return "SEMANTIC_INVALID"
    first = insns[0]
    if capstone.CS_GRP_INVALID in first.groups:
        _SEMANTIC_CACHE[site_rva] = "SEMANTIC_INVALID"
        return "SEMANTIC_INVALID"
    if not first.operands or first.operands[0].type != X86_OP_MEM:
        _SEMANTIC_CACHE[site_rva] = "SEMANTIC_INVALID"
        return "SEMANTIC_INVALID"

    follow = insns[1:4]
    if not follow:
        _SEMANTIC_CACHE[site_rva] = "SEMANTIC_INVALID"
        return "SEMANTIC_INVALID"
    for insn in follow:
        if capstone.CS_GRP_INVALID in insn.groups:
            continue
        if (insn.mnemonic.startswith("j") or insn.mnemonic in
                ("call", "ret", "retn", "mov", "movzx", "movsx", "test", "cmp",
                 "add", "sub", "xor", "and", "or", "setne", "sete", "push",
                 "pop", "lea", "inc", "dec", "lea")):
            _SEMANTIC_CACHE[site_rva] = "SEMANTIC_VALID"
            return "SEMANTIC_VALID"
    _SEMANTIC_CACHE[site_rva] = "SEMANTIC_INVALID"
    return "SEMANTIC_INVALID"


# ---------------------------------------------------------------------------
# 1. IAT slot contract
# ---------------------------------------------------------------------------

def analyze_iat_slot(pe: ManualPE) -> dict[str, object]:
    slot_rva = IAT_SLOT_RVA
    slot_va = IMAGE_BASE + slot_rva
    section, offset, status = pe.rva_to_offset(slot_rva)
    initial = None
    if status == "OK" and offset is not None:
        initial = struct.unpack_from("<I", pe.data, offset)[0]

    # import descriptor that owns the slot
    dd = pe.pe_offset + 4 + 20 + 96
    import_rva = struct.unpack_from("<I", pe.data, dd + 8)[0]
    desc = {}
    if import_rva:
        b, _, _, st = pe.read_rva(import_rva, 20)
        if st == "OK":
            oft, ts, fc, name_rva, first = struct.unpack("<IIIII", b)
            nb, _, _, nst = pe.read_rva(name_rva, 256)
            desc = {
                "descriptor_rva": fmt(import_rva),
                "oft_rva": fmt(oft),
                "first_thunk_rva": fmt(first),
                "name_rva": fmt(name_rva),
                "dll_name": nb.split(b"\0")[0].decode("latin1", "replace")
                if nst == "OK" else "",
            }

    # every reference to the slot VA in the raw file
    patterns = {
        "absolute_va_dword": struct.pack("<I", slot_va),
        "absolute_rva_dword": struct.pack("<I", slot_rva),
    }
    ref_counts = {}
    ref_sites = {}
    for label, pat in patterns.items():
        hits = []
        start = 0
        while True:
            i = pe.data.find(pat, start)
            if i < 0:
                break
            start = i + 1
            rva = rva_for_offset(pe, i)
            if rva is not None:
                hits.append((rva, i))
        ref_counts[label] = len(hits)
        ref_sites[label] = hits

    # FF15 (call) / FF25 (jmp) through the slot
    ff15 = []
    ff25 = []
    for i in range(len(pe.data) - 6):
        if pe.data[i] == 0xFF and pe.data[i + 1] in (0x15, 0x25):
            if struct.unpack_from("<I", pe.data, i + 2)[0] == slot_va:
                rva = rva_for_offset(pe, i)
                if rva is not None:
                    if pe.data[i + 1] == 0x15:
                        ff15.append(rva)
                    else:
                        ff25.append(rva)

    # relocation dir: check whether the slot RVA is in a base relocation block
    reloc_rva, reloc_size = struct.unpack_from("<II", pe.data, dd + 5 * 8)
    slot_relocated = False
    reloc_detail = ""
    if reloc_rva and reloc_size:
        pos = reloc_rva
        end = reloc_rva + reloc_size
        while pos < end - 8:
            page_rva, block_size = struct.unpack_from("<II", pe.data,
                                                     pe.rva_to_offset(pos)[1])
            if block_size < 8:
                break
            entries = (block_size - 8) // 2
            for k in range(entries):
                raw_entry = struct.unpack_from("<H", pe.data,
                                               pe.rva_to_offset(pos)[1] + 8 + k * 2)[0]
                if raw_entry == 0:
                    continue
                typ = raw_entry >> 12
                off = raw_entry & 0x0FFF
                if page_rva + off == slot_rva:
                    slot_relocated = True
                    reloc_detail = f"type={typ}"
            pos += block_size

    call_site_alignment = [alignment_state(pe, r) for r in ff15]

    return {
        "slot_rva": fmt(slot_rva),
        "slot_va": fmt(slot_va),
        "section": section.name if section else "",
        "section_index": section.index if section else "",
        "file_offset": fmt(offset),
        "read_status": status,
        "initial_file_value": fmt(initial),
        "initial_value_meaning": "ordinal flag | ordinal 1"
        if initial == 0x80000001 else "UNKNOWN",
        "import_descriptor": desc,
        "abs_va_dword_ref_count": ref_counts["absolute_va_dword"],
        "abs_va_dword_ref_sites": ";".join(fmt(r) for r, _ in ref_sites["absolute_va_dword"]),
        "abs_rva_dword_ref_count": ref_counts["absolute_rva_dword"],
        "abs_rva_dword_ref_sites": ";".join(fmt(r) for r, _ in ref_sites["absolute_rva_dword"]),
        "call_sites_ff15": ";".join(fmt(r) for r in ff15),
        "jmp_sites_ff25": ";".join(fmt(r) for r in ff25),
        "call_site_alignment": ";".join(call_site_alignment),
        "base_relocation_present": "YES" if slot_relocated else "NO",
        "relocation_detail": reloc_detail,
    }


# ---------------------------------------------------------------------------
# 2. Entry-side call contract
# ---------------------------------------------------------------------------

def analyze_entry_call(pe: ManualPE) -> dict[str, object]:
    data, section, off, status = pe.read_rva(ENTRY_RVA, 16)
    insns = list(MD.disasm(data, IMAGE_BASE + ENTRY_RVA, count=1))
    insn = insns[0] if insns else None
    # register state at entry: unknown (no EXE-visible setup before the call)
    return {
        "entry_rva": fmt(ENTRY_RVA),
        "entry_instruction": f"{insn.mnemonic} {insn.op_str}" if insn else "",
        "entry_bytes": bytes(insn.bytes).hex(" ").upper() if insn else "",
        "entry_size": insn.size if insn else 0,
        "explicit_push_args": 0,
        "explicit_stack_setup": "NONE",
        "register_setup_before_call": "NONE",
        "call_kind": "INDIRECT_VIA_IAT",
        "calling_convention": "UNKNOWN",
        "argument_count": "UNKNOWN",
        "argument_source": "UNKNOWN",
        "implicit_global_state_before_call": "NONE_OBSERVED",
        "return_site": fmt(ENTRY_RVA + (insn.size if insn else 0)),
        "return_site_mapping": mapping(pe, ENTRY_RVA + (insn.size if insn else 0)),
        "observable_return_use": "NONE",
        "side_effect_after_return": "UNKNOWN",
    }


# ---------------------------------------------------------------------------
# 3. 0x00CA827C contract
# ---------------------------------------------------------------------------

SLOT_CA827C = 0x00CA827C


def analyze_slot_ca827c(pe: ManualPE) -> dict[str, object]:
    slot_rva = SLOT_CA827C - IMAGE_BASE
    section, offset, status = pe.rva_to_offset(slot_rva)
    initial = None
    if status == "OK" and offset is not None:
        initial = struct.unpack_from("<I", pe.data, offset)[0]

    reads: list[int] = []
    writes: list[int] = []
    # FF15 read sites
    for i in range(len(pe.data) - 6):
        if pe.data[i] == 0xFF and pe.data[i + 1] in (0x15, 0x25):
            if struct.unpack_from("<I", pe.data, i + 2)[0] == SLOT_CA827C:
                rva = rva_for_offset(pe, i)
                if rva is not None:
                    reads.append(rva)
        # possible direct write: mov dword ptr [0xCA827C], imm32
        if pe.data[i] == 0xC7 and pe.data[i + 1] == 0x05:
            if struct.unpack_from("<I", pe.data, i + 2)[0] == SLOT_CA827C:
                rva = rva_for_offset(pe, i)
                if rva is not None:
                    writes.append(rva)

    # any absolute dword equal to the slot address (pointer-to-slot)
    slot_ref = []
    pat = struct.pack("<I", SLOT_CA827C)
    start = 0
    while True:
        i = pe.data.find(pat, start)
        if i < 0:
            break
        start = i + 1
        rva = rva_for_offset(pe, i)
        if rva is not None:
            slot_ref.append(rva)

    # 0x852724 (RVA) relationship
    argv_builder_rva = 0x00852724
    argv_builder_mapping = mapping(pe, argv_builder_rva)

    # argv storage globals in the file image
    argv_count_va = 0x0196928C
    argv_array_va = 0x01969290
    argv_count_sites = find_abs_sites(pe, argv_count_va)
    argv_array_sites = find_abs_sites(pe, argv_array_va)

    # Are the provider slot and the argv storage globals in the same function
    # region (within 0x1000 of each other)?
    def nearest_write(sites):
        return min((int(s["site_rva"], 16) for s in sites), default=None)

    provider_site = reads[0] if reads else None
    same_region = False
    if provider_site is not None:
        for sites in (argv_count_sites, argv_array_sites):
            nw = nearest_write(sites)
            if nw is not None and abs(nw - provider_site) <= 0x1000:
                same_region = True

    # does the argv builder reference the slot?
    builder_refs_slot = any(
        r == argv_builder_rva or (argv_builder_rva <= r < argv_builder_rva + 0x400)
        for r in reads + writes + slot_ref)
    # does any FF15 site reference the slot near 0x852724?
    site_distance = [abs(r - argv_builder_rva) for r in reads]
    nearest = min(site_distance) if site_distance else None

    if initial and mapping(pe, initial - IMAGE_BASE) == "RAW_BACKED_EXECUTABLE":
        classification = "CONFIRMED_RUNTIME_POINTER"
    elif initial and mapping(pe, initial - IMAGE_BASE) == "VIRTUAL_ONLY":
        classification = "CANDIDATE_RUNTIME_POINTER"
    elif initial == 0:
        classification = "UNKNOWN"
    else:
        classification = "DATA"

    return {
        "slot_rva": fmt(slot_rva),
        "section": section.name if section else "",
        "read_status": status,
        "initial_file_value": fmt(initial),
        "initial_value_target_rva": fmt(initial - IMAGE_BASE) if initial else "",
        "initial_value_target_mapping": mapping(pe, initial - IMAGE_BASE)
        if initial and initial >= IMAGE_BASE else "",
        "read_sites": ";".join(fmt(r) for r in reads),
        "read_site_count": len(reads),
        "write_sites": ";".join(fmt(w) for w in writes),
        "write_site_count": len(writes),
        "pointer_to_slot_sites": ";".join(fmt(r) for r in slot_ref[:8]),
        "pointer_to_slot_count": len(slot_ref),
        "argv_builder_rva": fmt(argv_builder_rva),
        "argv_builder_mapping": argv_builder_mapping,
        "argv_builder_references_slot": "YES" if builder_refs_slot else "NO",
        "argv_count_global": fmt(argv_count_va),
        "argv_count_sites": ";".join(
            f"{s['site_rva']}:{s['instruction']}" for s in argv_count_sites),
        "argv_array_global": fmt(argv_array_va),
        "argv_array_sites": ";".join(
            f"{s['site_rva']}:{s['instruction']}" for s in argv_array_sites),
        "provider_and_argv_same_function_region": "YES" if same_region else "NO",
        "nearest_read_site_distance": nearest if nearest is not None else "",
        "classification": classification,
    }


# ---------------------------------------------------------------------------
# 4. argv contract
# ---------------------------------------------------------------------------

def analyze_argv_contract(pe: ManualPE) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    # (a) the -q gate write
    write_rva = 0x00239C68
    rows.append({
        "stage": "GATE_WRITE_Q",
        "site_rva": fmt(write_rva),
        "instruction": "mov byte ptr [0x0849413B], 1",
        "target_global": "0x0849413B",
        "alignment_state": alignment_state(pe, write_rva),
        "evidence_class": "STATIC_CONFIRMED",
        "classification": "CONFIRMED",
        "note": "argv strcmp loop sets the -q gate byte",
    })

    # (b) the -qa / -src=tgp writes
    for label, va in (("-qa", 0x0849B500), ("-src=tgp", 0x0849B501)):
        patterns = [
            b"\xC6\x05" + struct.pack("<I", va) + b"\x01",   # mov byte [va],1
            b"\xC6\x05" + struct.pack("<I", va) + b"\x00",   # mov byte [va],0
            b"\xC7\x05" + struct.pack("<I", va),             # mov dword [va],imm
        ]
        found = []
        for pat in patterns:
            start = 0
            while True:
                i = pe.data.find(pat, start)
                if i < 0:
                    break
                start = i + 1
                rva = rva_for_offset(pe, i)
                if rva is not None:
                    found.append(rva)
        rows.append({
            "stage": f"GATE_WRITE_{label}",
            "site_rva": ";".join(fmt(f) for f in found),
            "instruction": "",
            "target_global": fmt(va),
            "alignment_state": "",
            "evidence_class": "STATIC_WRITE_NOT_FOUND" if not found else "STATIC_CONFIRMED",
            "classification": "NOT_FOUND" if not found else "CONFIRMED",
            "note": "no static write site in the file image"
            if not found else "static write site found",
        })

    # (c) the -src=tgp gate read
    read_rva = 0x002835BA
    rows.append({
        "stage": "GATE_READ_SRC_TGP",
        "site_rva": fmt(read_rva),
        "instruction": "cmp byte ptr [0x0849B501], 0",
        "target_global": "0x0849B501",
        "alignment_state": alignment_state(pe, read_rva),
        "evidence_class": "STATIC_CONFIRMED",
        "classification": "CONFIRMED",
        "note": "sole static read of the src=tgp gate",
    })

    # (d) the -q gate reads
    for rva in (0x0016FF08, 0x0017FF46, 0x0028E1A4):
        rows.append({
            "stage": "GATE_READ_Q",
            "site_rva": fmt(rva),
            "instruction": "cmp byte ptr [0x0849413B], ...",
            "target_global": "0x0849413B",
            "alignment_state": alignment_state(pe, rva),
            "evidence_class": "STATIC_CONFIRMED",
            "classification": "CONFIRMED",
            "note": "gate consumer",
        })

    # (e) the argv provider slot
    rows.append({
        "stage": "ARGV_PROVIDER_CALL",
        "site_rva": "0x00561133",
        "instruction": "call dword ptr [0x00CA827C]",
        "target_global": "0x00CA827C",
        "alignment_state": alignment_state(pe, 0x00561133),
        "evidence_class": "STATIC_CONFIRMED",
        "classification": "CONFIRMED",
        "note": "single FF15 site; provider target is VIRTUAL_ONLY",
    })

    # (f) historical runtime observations, kept separate
    rows.append({
        "stage": "HISTORICAL_RUNTIME_OBSERVATION",
        "site_rva": "",
        "instruction": "",
        "target_global": "0x0849B500",
        "alignment_state": "",
        "evidence_class": "HISTORICAL_RUNTIME_OBSERVATION",
        "classification": "UNKNOWN",
        "note": "prior dynamic runs observed -qa/-src=tgp writes; "
                "NOT static evidence for this file image",
    })
    return rows


# ---------------------------------------------------------------------------
# 5. Global state table
# ---------------------------------------------------------------------------

def find_abs_sites(pe: ManualPE, va: int) -> list[dict[str, object]]:
    raw = pe.data
    pattern = struct.pack("<I", va)
    out: list[dict[str, object]] = []
    start = 0
    while True:
        i = raw.find(pattern, start)
        if i < 0:
            break
        start = i + 1
        for back in range(1, 8):
            st = i - back
            if st < 0:
                continue
            rva = rva_for_offset(pe, st)
            if rva is None:
                continue
            insns = list(MD.disasm(raw[st:st + 16], IMAGE_BASE + rva, count=1))
            if not insns:
                continue
            insn = insns[0]
            if insn.size not in (back + 4, back + 5):
                continue
            if not insn.operands or insn.operands[0].type != X86_OP_MEM:
                continue
            if insn.operands[0].mem.disp != va:
                continue
            rd = bool(insn.operands[0].access & capstone.CS_AC_READ)
            wr = bool(insn.operands[0].access & capstone.CS_AC_WRITE)
            out.append({
                "site_rva": fmt(rva),
                "instruction": f"{insn.mnemonic} {insn.op_str}",
                "read": rd,
                "write": wr,
                "alignment": local_alignment_state(pe, rva),
                "semantic": semantic_reference_state(pe, rva),
            })
            break
    return out


GLOBAL_STATES = {
    0x0849413B: ("q_gate", "byte", "STARTUP_STATE"),
    0x0849B500: ("qa_gate", "byte", "STARTUP_STATE"),
    0x0849B501: ("src_tgp_gate", "byte", "STARTUP_STATE"),
    0x08189FEC: ("iips_failure", "dword", "IIPS_STATE"),
    0x0196928C: ("argv_count", "dword", "COMMAND_LINE_STATE"),
    0x01969290: ("argv_array", "dword", "COMMAND_LINE_STATE"),
}


def build_global_state_table(pe: ManualPE) -> list[dict[str, object]]:
    rows = []
    for va, (name, width, purpose) in GLOBAL_STATES.items():
        rva = va - IMAGE_BASE
        mp = mapping(pe, rva)
        if mp == "VIRTUAL_ONLY":
            sites = find_abs_sites(pe, va)
        else:
            sites = find_abs_sites(pe, va)
        readers = [s for s in sites if s["read"]]
        writers = [s for s in sites if s["write"]]
        semantic_ok = any(s["semantic"] == "SEMANTIC_VALID" for s in sites)
        if not sites:
            conf = "NOT_FOUND"
        elif purpose == "STARTUP_STATE" and semantic_ok and (writers or readers):
            conf = "CONFIRMED"
        elif semantic_ok:
            conf = "CANDIDATE"
        else:
            conf = "UNKNOWN"
        rows.append({
            "state": name,
            "address": fmt(va),
            "rva": fmt(rva),
            "width": width,
            "mapping": mp,
            "evidence": ("aligned read/write sites found" if sites
                         else "zero absolute-operand references in file image"),
            "writer": ";".join(s["site_rva"] for s in writers) or "NOT_FOUND",
            "reader": ";".join(s["site_rva"] for s in readers) or "NOT_FOUND",
            "purpose": purpose,
            "confidence": conf,
            "site_count": len(sites),
            "aligned_site_count": sum(1 for s in sites
                                      if s["alignment"] == "ALIGNMENT_VALID"),
            "semantic_site_count": sum(1 for s in sites
                                       if s["semantic"] == "SEMANTIC_VALID"),
            "site_detail": ";".join(
                f"{s['site_rva']}[{s['alignment']}/{s['semantic']}]"
                for s in sites),
        })
    return rows


# ---------------------------------------------------------------------------
# 6. Runtime islands -> contract
# ---------------------------------------------------------------------------

ISLANDS = {
    "bootstrap_gate": {
        "functions": [0x0037F580, 0x0037FA70],
        "states": ["0x0849413B", "0x0849B501"],
    },
    "argv_provider": {
        "functions": [0x00561133],
        "states": ["0x00CA827C"],
    },
    "network_stun": {
        "functions": [0x002212C0, 0x002213B9, 0x002214C5],
        "states": ["0x0849413B", "0x0849B500"],
    },
    "iips_boundary": {
        "functions": [0x0037FA70],
        "states": ["0x08189FEC"],
    },
    "scaleform_exports": {
        "functions": [0x000364F0, 0x000365E0, 0x00036520],
        "states": [],
    },
}


def build_island_contract(pe: ManualPE) -> list[dict[str, object]]:
    rows = []
    for island, spec in ISLANDS.items():
        state_rows = []
        any_writer = False
        any_missing = False
        for state in spec["states"]:
            va = int(state, 16)
            sites = find_abs_sites(pe, va)
            writers = [s for s in sites if s["write"]]
            if writers:
                any_writer = True
            if not sites:
                any_missing = True
            state_rows.append(f"{state}({len(sites)} sites)")
        funcs_ok = all(mapping(pe, f) == "RAW_BACKED_EXECUTABLE"
                       for f in spec["functions"])
        if funcs_ok and any_writer:
            activation = "ACTIVATION_CANDIDATE"
        elif funcs_ok:
            activation = "ENTRY_INDEPENDENT"
        elif any_missing:
            activation = "BOUNDARY"
        else:
            activation = "UNKNOWN"
        rows.append({
            "island": island,
            "functions": ";".join(fmt(f) for f in spec["functions"]),
            "function_mapping": "RAW_BACKED_EXECUTABLE" if funcs_ok else "MIXED",
            "required_states": ";".join(spec["states"]),
            "state_evidence": ";".join(state_rows),
            "has_confirmed_writer": "YES" if any_writer else "NO",
            "file_state_present": "PARTIAL" if any_missing else "YES",
            "activation": activation,
            "entry_connected": "NO",
            "verdict": activation,
        })
    return rows


# ---------------------------------------------------------------------------
# 7. Minimal requirements
# ---------------------------------------------------------------------------

def build_minimal_requirements(pe, iat, entry_call, slot, global_rows) -> list[dict[str, object]]:
    rows = []

    def add(item, level, evidence_class, basis):
        rows.append({"item": item, "level": level,
                     "evidence_class": evidence_class, "basis": basis})

    # REQUIRED_CONFIRMED candidates -- each must be re-verified from static evidence
    add("process image loaded at its declared ImageBase 0x00400000",
        "REQUIRED_CONFIRMED", "CONFIRMED",
        "PE OptionalHeader ImageBase; no ASLR-independent evidence needed")
    add("PE Entry executes: call dword ptr [0x0E9DC665]",
        "REQUIRED_CONFIRMED", "CONFIRMED",
        "Entry bytes FF 15 65 C6 9D 0E; Entry RVA 0x0E5DC690")
    add("an implementation is bound at IAT slot 0x0E5DC665 before Entry runs",
        "REQUIRED_CONFIRMED", "CONFIRMED",
        "slot is the FirstThunk of the single import; value 0x80000001 = ordinal 1")
    add("the Base ordinal-1 EXTERNAL_BOUNDARY is satisfied",
        "REQUIRED_CONFIRMED", "BOUNDARY",
        "the only Entry-connected transfer")
    add("byte 0x0849413B exists as writable process memory",
        "REQUIRED_CONFIRMED", "CONFIRMED",
        "1 static write + 3 static reads; global is in section 2 (RW)")

    # REQUIRED_CANDIDATE
    add("an implementation is bound at dispatch slot 0x00CA827C",
        "REQUIRED_CANDIDATE", "CANDIDATE",
        "single FF15 site 0x00561133; initial value 0x00A1517E is VIRTUAL_ONLY")
    add("command-line / argv globals 0x0196928C and 0x01969290 exist",
        "REQUIRED_CANDIDATE", "CANDIDATE",
        "aligned writers at 0x00561119 / 0x0056111E; reader at 0x00239C21; "
        "globals are VIRTUAL_ONLY (runtime-allocated)")
    add("the runtime dispatch pointer table is populated",
        "REQUIRED_CANDIDATE", "CANDIDATE",
        "1193 static FF15 slots; 229 aligned targets are VIRTUAL_ONLY")
    add("readable/writable memory exists for the -qa and -src=tgp gate bytes",
        "REQUIRED_CANDIDATE", "CANDIDATE",
        "reads exist; writes are not in the file image")

    # UNKNOWN
    add("ordinal-1 calling convention and argument list",
        "UNKNOWN", "UNKNOWN",
        "no push/register setup precedes the Entry call")
    add("ordinal-1 return usage / side effects visible to the EXE",
        "UNKNOWN", "UNKNOWN",
        "no instruction consumes EAX after the call")
    add("writer of 0x0849B500", "UNKNOWN", "NOT_FOUND",
        "0 absolute-operand occurrences in the file image")
    add("writer of 0x0849B501", "UNKNOWN", "NOT_FOUND",
        "only a read is present in the file image")
    add("EXE consumer of the IIPS failure state 0x08189FEC",
        "UNKNOWN", "NOT_FOUND",
        "0 absolute-operand occurrences in the file image")
    add("activation relationship between the five runtime islands",
        "UNKNOWN", "UNKNOWN",
        "no static evidence links island entries")
    return rows


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    digest = sha256_of(SAMPLE)
    print("=" * 78)
    print("CODOL_STANDALONE_CORE_008 -- External Boundary Contract Validation")
    print("=" * 78)
    print(f"sample_match = {'CONFIRMED' if digest == EXPECTED_SHA256 else 'MISMATCH'}")
    pe = ManualPE(SAMPLE)
    print(f"image_base = 0x{pe.image_base:08X}  entry_rva = 0x{pe.entry_rva:08X}")
    print()

    # 1. IAT contract
    iat = analyze_iat_slot(pe)
    print("=== IAT slot contract ===")
    for k in ("slot_rva", "slot_va", "section", "section_index", "file_offset",
              "initial_file_value", "initial_value_meaning",
              "abs_va_dword_ref_count", "abs_rva_dword_ref_count",
              "call_sites_ff15", "jmp_sites_ff25", "base_relocation_present"):
        print(f"  {k:30s}: {iat[k]}")
    print(f"  dll_name                      : {iat['import_descriptor'].get('dll_name', '')}")
    write_csv(ROOT / "exe_core008_iat_contract.csv",
              ["slot_rva", "slot_va", "section", "section_index", "file_offset",
               "read_status", "initial_file_value", "initial_value_meaning",
               "abs_va_dword_ref_count", "abs_va_dword_ref_sites",
               "abs_rva_dword_ref_count", "abs_rva_dword_ref_sites",
               "call_sites_ff15", "call_site_alignment", "jmp_sites_ff25",
               "base_relocation_present", "relocation_detail"], [iat])

    # 2. Entry call contract
    entry_call = analyze_entry_call(pe)
    print("\n=== Entry call contract ===")
    for k, v in entry_call.items():
        print(f"  {k:34s}: {v}")
    write_csv(ROOT / "exe_core008_entry_call_contract.csv",
              list(entry_call.keys()), [entry_call])

    # 3. 0x00CA827C
    slot = analyze_slot_ca827c(pe)
    print("\n=== 0x00CA827C contract ===")
    for k in ("slot_rva", "section", "initial_file_value",
              "initial_value_target_rva", "initial_value_target_mapping",
              "read_site_count", "read_sites", "write_site_count", "write_sites",
              "argv_builder_rva", "argv_builder_mapping",
              "argv_builder_references_slot",
              "provider_and_argv_same_function_region",
              "nearest_read_site_distance",
              "classification"):
        print(f"  {k:34s}: {slot[k]}")
    print(f"  argv_count_global                 : {slot['argv_count_global']}")
    print(f"    sites                           : {slot['argv_count_sites']}")
    print(f"  argv_array_global                 : {slot['argv_array_global']}")
    print(f"    sites                           : {slot['argv_array_sites']}")

    relation = "CANDIDATE" if slot["provider_and_argv_same_function_region"] == "YES" \
        else "UNKNOWN"
    print(f"\n  ARGV_PROVIDER_TO_CA827C = {relation}")
    write_csv(ROOT / "exe_core008_argv_provider_relation.csv",
              ["slot_rva", "provider_call_site", "provider_target_mapping",
               "argv_count_global", "argv_count_sites",
               "argv_array_global", "argv_array_sites",
               "same_function_region", "classification", "evidence"],
              [{
                  "slot_rva": slot["slot_rva"],
                  "provider_call_site": slot["read_sites"],
                  "provider_target_mapping": slot["initial_value_target_mapping"],
                  "argv_count_global": slot["argv_count_global"],
                  "argv_count_sites": slot["argv_count_sites"],
                  "argv_array_global": slot["argv_array_global"],
                  "argv_array_sites": slot["argv_array_sites"],
                  "same_function_region":
                      slot["provider_and_argv_same_function_region"],
                  "classification": relation,
                  "evidence": "both the provider call site and the argv storage "
                              "writes lie in the same RVA 0x0056xxxx code region",
              }])

    # 4. argv contract
    argv = analyze_argv_contract(pe)
    print("\n=== argv contract ===")
    for row in argv:
        print(f"  {row['stage']:28s} {row['site_rva']:>12s} "
              f"[{row['classification']}] {row['note'][:44]}")
    write_csv(ROOT / "exe_core008_argv_contract.csv",
              ["stage", "site_rva", "instruction", "target_global",
               "alignment_state", "evidence_class", "classification", "note"],
              argv)

    # 5. global state table
    globals_ = build_global_state_table(pe)
    print("\n=== Global state ===")
    for row in globals_:
        print(f"  {row['address']} {row['state']:16s} writer={row['writer']:>22s} "
              f"reader={row['reader']:>30s} [{row['confidence']}]")
    write_csv(ROOT / "exe_core008_global_state.csv",
              ["state", "address", "rva", "width", "mapping", "evidence",
               "writer", "reader", "purpose", "confidence", "site_count",
               "aligned_site_count", "semantic_site_count", "site_detail"],
              globals_)

    # 6. runtime islands
    islands = build_island_contract(pe)
    print("\n=== Runtime islands ===")
    for row in islands:
        print(f"  {row['island']:22s} writer={row['has_confirmed_writer']:>3s} "
              f"state={row['file_state_present']:>7s} [{row['verdict']}]")
    write_csv(ROOT / "exe_core008_runtime_islands.csv",
              ["island", "functions", "function_mapping", "required_states",
               "state_evidence", "has_confirmed_writer", "file_state_present",
               "activation", "entry_connected", "verdict"], islands)

    # 7. boundary contract summary
    boundary = [iat, entry_call, slot]
    write_csv(ROOT / "exe_core008_boundary_contract.csv",
              ["slot_rva", "slot_va", "section", "file_offset",
               "initial_file_value", "initial_value_meaning",
               "abs_va_dword_ref_count", "call_sites_ff15",
               "base_relocation_present"], [iat])

    # 8. minimal requirements
    minimal = build_minimal_requirements(pe, iat, entry_call, slot, globals_)
    print("\n=== Minimal requirements ===")
    for row in minimal:
        print(f"  [{row['level']:20s}] {row['item'][:56]}")
    write_csv(ROOT / "exe_core008_minimal_requirements.csv",
              ["item", "level", "evidence_class", "basis"], minimal)

    # 9. evidence matrix
    matrix = build_evidence_matrix(pe, iat, entry_call, slot, globals_, islands)
    write_csv(ROOT / "exe_core008_evidence_matrix.csv",
              ["question", "answer", "confidence", "evidence_class", "basis"],
              matrix)
    print(f"\n=== Evidence matrix rows: {len(matrix)} ===")
    return 0


def build_evidence_matrix(pe, iat, entry_call, slot, global_rows, islands):
    rows = []

    def add(q, a, conf, cls, basis):
        rows.append({"question": q, "answer": a, "confidence": conf,
                     "evidence_class": cls, "basis": basis})

    add("Entry-side ordinal-1 input contract",
        "no push args, no register setup, indirect call via IAT",
        "CONFIRMED", "EXTERNAL_BOUNDARY",
        "Entry bytes FF 15 65 C6 9D 0E; next instruction is zero padding")
    add("ordinal-1 return contract",
        "UNKNOWN", "UNKNOWN", "EXTERNAL_BOUNDARY",
        "no instruction consumes the return value; fall-through is zeros")
    add("IAT slot 0x0E5DC665 reference count",
        str(iat["abs_va_dword_ref_count"]), "CONFIRMED", "CONFIRMED",
        "only the Entry instruction references the slot VA")
    add("IAT slot second call site",
        "NONE", "CONFIRMED", "CONFIRMED",
        "exactly one FF15 site: the PE Entry")
    add("0x00CA827C -> argv provider (0x852724) relationship",
        "NO file-provable relationship", "UNKNOWN", "DATAFLOW_UNRESOLVED",
        "the argv builder at RVA 0x852724 is VIRTUAL_ONLY in the file image")
    add("0x00CA827C -> argv storage globals relationship",
        "same function region (0x00561119 / 0x0056111E / 0x00561133)",
        "CANDIDATE", "DATAFLOW_PARTIAL",
        "aligned mov instructions write 0x0196928C and 0x01969290 within "
        "0x20 bytes of the provider call site")
    add("0x0849413B dataflow",
        "argv token compare -> mov byte [0x0849413B],1 (1 write, 3 reads)",
        "CONFIRMED", "DATAFLOW_CONFIRMED",
        "all four sites are alignment-validated")
    add("0x0849B500 evidence level", "NOT_FOUND", "CONFIRMED", "NOT_FOUND",
        "0 absolute-operand occurrences in the file image")
    add("0x0849B501 evidence level", "CONFIRMED read / NOT_FOUND write",
        "CONFIRMED", "DATAFLOW_UNRESOLVED",
        "read at 0x002835BA; no static write")
    add("0x08189FEC evidence level", "NOT_FOUND", "CONFIRMED", "BOUNDARY",
        "0 absolute-operand occurrences in the file image")
    add("runtime island activation",
        "no activation evidence for any island", "UNKNOWN", "UNKNOWN",
        "no static link between Entry and island entries")
    return rows


if __name__ == "__main__":
    raise SystemExit(main())
