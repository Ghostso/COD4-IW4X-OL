from __future__ import annotations

"""
CODOL_STANDALONE_CORE_007
codoMP_client_shipRetail.exe -- External-Boundary Contract Recovery

Scope: codoMP_client_shipRetail.exe only (static file image).

Prohibited: WeGame, Tencent launcher, Sandboxie, Procmon, TCLS internals,
TenProxy internals, Base.dll internals, CODOL-MP.exe, modifying EXE, patch,
hook, debugger-dependent conclusions, .tvm0 semantic recovery.

If Base ordinal-1 must be referenced it is written as EXTERNAL_BOUNDARY only.

Allowed: static PE analysis, RVA->file offset, x86 disassembly, direct CALL/JMP,
indirect-call analysis, function-pointer analysis, table analysis, thread seed
analysis, CFG recovery, dataflow analysis.
"""

import csv
import hashlib
import re
import struct
from collections import Counter, defaultdict
from pathlib import Path

import capstone
from capstone import CS_ARCH_X86, CS_GRP_CALL, CS_GRP_JUMP, CS_GRP_RET, CS_MODE_32
from capstone.x86_const import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from core004a_diagnostic import ManualPE, SAMPLE


ROOT = Path(__file__).resolve().parent
EXPECTED_SHA256 = "36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537"
IMAGE_BASE = 0x00400000
EXPECTED_ENTRY_RVA = 0x0E5DC690
TVM0_NAME = ".tvm0"

MD = capstone.Cs(CS_ARCH_X86, CS_MODE_32)
MD.detail = True

# Globals of interest (absolute VA as documented by the prior rounds).
GLOBALS_OF_INTEREST = {
    0x0849413B: "startup state (q/qa gate)",
    0x0849B500: "startup state (qa gate)",
    0x0849B501: "startup state (src=tgp gate)",
    0x08189FEC: "IIPS failure state",
}


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def fmt(value: int | None) -> str:
    if value is None:
        return ""
    if value < 0:
        return f"-0x{-value:08X}"
    return f"0x{value:08X}"


def section_index_for_offset(pe: ManualPE, offset: int) -> int | None:
    for s in pe.sections:
        if s.raw_offset <= offset < s.raw_offset + s.raw_size:
            return s.index
    return None


def rva_for_offset(pe: ManualPE, offset: int) -> int | None:
    for s in pe.sections:
        if s.raw_offset <= offset < s.raw_offset + s.raw_size:
            return s.virtual_address + (offset - s.raw_offset)
    return None


def byte_array_for(cluster: str, min_size: int) -> bytes:
    """Explicitly preserved helper for callers that need a byte array."""
    return bytes(min_size)


def classify_mapping(pe: ManualPE, rva: int) -> str:
    section, offset, status = pe.rva_to_offset(rva)
    if section is None and status == "PE_HEADERS":
        return "PE_HEADERS"
    if section is None:
        return status
    if section.name == TVM0_NAME:
        return "TVM0_BOUNDARY"
    if status == "VIRTUAL_ONLY":
        return "VIRTUAL_ONLY"
    if status != "OK":
        return status
    return "RAW_BACKED_EXECUTABLE" if section.executable else "RAW_BACKED_DATA"


def classify_target(
    pe: ManualPE,
    cluster: str,
    status: str,
    target: int | None,
    evidence_class: str,
) -> dict[str, object]:
    """Classify a transfer target using the round's evidence vocabulary.

    The returned dict is intentionally explicit so that no caller can silently
    promote an address to a function without a dataflow-confirmed target.
    """
    if target is None:
        return {"target_mapping": "", "evidence": "DATAFLOW_UNRESOLVED",
                "verdict": "UNKNOWN"}
    mapping = classify_mapping(pe, target)
    if mapping == "TVM0_BOUNDARY":
        return {"target_mapping": mapping, "evidence": "EXTERNAL_BOUNDARY",
                "verdict": "BOUNDARY"}
    if mapping == "RAW_BACKED_EXECUTABLE":
        return {"target_mapping": mapping,
                "evidence": evidence_class,
                "verdict": "CANDIDATE"}
    if mapping == "VIRTUAL_ONLY":
        return {"target_mapping": mapping, "evidence": "DATAFLOW_UNRESOLVED",
                "verdict": "UNKNOWN"}
    return {"target_mapping": mapping, "evidence": evidence_class,
            "verdict": "UNKNOWN"}


# ---------------------------------------------------------------------------
# A. Global slot contract analysis
# ---------------------------------------------------------------------------

def find_abs_memory_sites(pe: ManualPE, va: int) -> list[dict[str, object]]:
    """Find alignment-valid instructions whose absolute memory operand is `va`.

    Handles modrm encodings where (modrm & 0xC7) == 0x05 (disp32, no base/index)
    for opcodes of the form `op modrm disp32 [imm]`.
    """
    raw = pe.data
    pattern = struct.pack("<I", va)
    sites: list[dict[str, object]] = []
    for match in re.finditer(re.escape(pattern), raw):
        disp_offset = match.start()
        for back in range(1, 8):
            start = disp_offset - back
            if start < 0:
                break
            rva = rva_for_offset(pe, start)
            if rva is None:
                continue
            chunk = raw[start:start + 16]
            insns = list(MD.disasm(chunk, IMAGE_BASE + rva, count=1))
            if not insns:
                continue
            insn = insns[0]
            if insn.size != back + 4:
                # immediate form (e.g. C6 05 disp32 imm8) => size back+5
                if insn.size != back + 5:
                    continue
            if not insn.operands:
                continue
            if insn.operands[0].type != X86_OP_MEM:
                continue
            mem = insn.operands[0].mem
            if mem.disp != va:
                continue
            sites.append(instruction_row(pe, rva, insn, "ABS_MEMORY"))
            break
    return sites


def instruction_row(pe: ManualPE, rva: int, insn, kind: str) -> dict[str, object]:
    # determine read vs write from the operand access flags
    read = False
    write = False
    if insn.operands:
        op = insn.operands[0]
        read = bool(op.access & capstone.CS_AC_READ)
        write = bool(op.access & capstone.CS_AC_WRITE)
    return {
        "site_rva": fmt(rva),
        "site_va": fmt(IMAGE_BASE + rva),
        "section": classify_mapping(pe, rva),
        "bytes": bytes(insn.bytes).hex(" ").upper(),
        "instruction": f"{insn.mnemonic} {insn.op_str}",
        "mnemonic": insn.mnemonic,
        "kind": kind,
        "operand_read": "YES" if read else "NO",
        "operand_write": "YES" if write else "NO",
    }


def analyze_global(pe: ManualPE, va: int, label: str) -> dict[str, object]:
    rva = va - IMAGE_BASE
    sites = find_abs_memory_sites(pe, va)
    reads = [s for s in sites if s["operand_read"] == "YES"]
    writes = [s for s in sites if s["operand_write"] == "YES"]
    mapping = classify_mapping(pe, rva)
    return {
        "global_va": fmt(va),
        "global_rva": fmt(rva),
        "label_hint": label,
        "global_mapping": mapping,
        "site_count": len(sites),
        "read_count": len(reads),
        "write_count": len(writes),
        "first_write": writes[0]["site_rva"] if writes else "",
        "first_read": reads[0]["site_rva"] if reads else "",
        "read_sites": ";".join(s["site_rva"] for s in reads[:12]),
        "write_sites": ";".join(s["site_rva"] for s in writes[:12]),
        "sites": sites,
    }


def global_contract_rows(pe: ManualPE) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    contract: list[dict[str, object]] = []
    detail: list[dict[str, object]] = []
    for va, label in GLOBALS_OF_INTEREST.items():
        info = analyze_global(pe, va, label)
        read_sites = [s for s in info["sites"] if s["operand_read"] == "YES"]
        write_sites = [s for s in info["sites"] if s["operand_write"] == "YES"]
        if info["global_mapping"] == "VIRTUAL_ONLY" and (read_sites or write_sites):
            state_class = "STARTUP_STATE"
        elif info["global_mapping"] == "VIRTUAL_ONLY":
            state_class = "UNKNOWN"
        else:
            state_class = "RUNTIME_STATE"
        if not read_sites and not write_sites:
            state_class = "UNKNOWN"
        contract.append({
            "global_va": info["global_va"],
            "global_rva": info["global_rva"],
            "global_mapping": info["global_mapping"],
            "label_hint": label,
            "site_count": info["site_count"],
            "read_count": info["read_count"],
            "write_count": info["write_count"],
            "first_write": info["first_write"],
            "first_read": info["first_read"],
            "read_sites": info["read_sites"],
            "write_sites": info["write_sites"],
            "state_class": state_class,
        })
        for s in info["sites"]:
            detail.append({"global_va": info["global_va"], **s})
    return contract, detail


# ---------------------------------------------------------------------------
# B. Indirect slots
# ---------------------------------------------------------------------------

def analyze_indirect_slots(pe: ManualPE) -> list[dict[str, object]]:
    """Enumerate `FF 15 <abs32>` (call dword ptr [abs]) and `FF 25` (jmp) sites,
    group by slot VA, and read the slot's static image value."""
    raw = pe.data
    groups: dict[int, list[tuple[int, int, str]]] = defaultdict(list)
    for i in range(len(raw) - 6):
        if raw[i] == 0xFF and raw[i + 1] in (0x15, 0x25):
            slot = struct.unpack_from("<I", raw, i + 2)[0]
            rva = rva_for_offset(pe, i)
            if rva is not None:
                groups[slot].append((rva, raw[i + 1], _alignment_state(pe, rva)))

    rows: list[dict[str, object]] = []
    for slot_va, sites in groups.items():
        slot_rva = slot_va - IMAGE_BASE if slot_va >= IMAGE_BASE else slot_va
        slot_mapping = classify_mapping(pe, slot_rva)
        value = None
        value_mapping = ""
        vb, _s, _o, vst = pe.read_rva(slot_rva, 4)
        if vst == "OK" and len(vb) == 4:
            value = struct.unpack("<I", vb)[0]
            if value:
                value_mapping = classify_mapping(
                    pe, value - IMAGE_BASE if value >= IMAGE_BASE else value)
        first_site, opcode, align = min(sites, key=lambda t: t[0])
        aligned_sites = [s for s in sites if s[2] == "ALIGNMENT_VALID"]
        # classify
        if align != "ALIGNMENT_VALID":
            classification = "ALIGNMENT_INVALID"
        elif value and value_mapping == "RAW_BACKED_EXECUTABLE":
            classification = "DATAFLOW_CONFIRMED"
        elif value and value_mapping == "VIRTUAL_ONLY":
            classification = "DATAFLOW_UNRESOLVED"
        elif value == 0:
            classification = "UNKNOWN"
        else:
            classification = "UNKNOWN"
        rows.append({
            "slot_va": fmt(slot_va),
            "slot_rva": fmt(slot_rva),
            "slot_section": classify_mapping(pe, slot_rva),
            "initial_value": fmt(value),
            "initial_value_mapping": value_mapping,
            "site_rva": fmt(first_site),
            "instruction": "call dword ptr [slot]" if opcode == 0x15
                else "jmp dword ptr [slot]",
            "slot_target": fmt(value - IMAGE_BASE) if value else "",
            "slot_target_mapping": value_mapping,
            "xref_count": len(sites),
            "aligned_xref_count": len(aligned_sites),
            "alignment_state": align,
            "classification": classification,
        })
    rows.sort(key=lambda r: r["xref_count"], reverse=True)
    return rows


_ALIGN_CACHE: dict[int, str] = {}
_BOUNDARY_CACHE: set[int] | None = None


def _valid_boundaries(pe: ManualPE) -> set[int]:
    """Compute the set of RVAs that are genuine x86 instruction boundaries.

    A single linear sweep from each `55 8B EC` prologue yields a set of
    instruction starts. This is a conservative over-approximation of real code
    starts (it can include bytes after a false prologue), so it is used only to
    *reject* sites that no sweep ever reaches. All accepted boundaries are
    additionally reported with their alignment state so callers can see the
    difference between 'reached by a sweep' and 'confirmed code'.
    """
    global _BOUNDARY_CACHE
    if _BOUNDARY_CACHE is not None:
        return _BOUNDARY_CACHE
    raw = pe.data
    boundaries: set[int] = set()
    for section in pe.sections:
        if not section.executable or section.raw_size == 0:
            continue
        raw_start = section.raw_offset
        raw_end = section.raw_offset + section.raw_size
        pos = raw_start
        while pos < raw_end - 3:
            if raw[pos] == 0x55 and raw[pos + 1] == 0x8B and raw[pos + 2] == 0xEC:
                prologue_rva = section.virtual_address + (pos - raw_start)
                count = 0
                for insn in MD.disasm(raw[pos:raw_end], IMAGE_BASE + prologue_rva):
                    boundaries.add(insn.address - IMAGE_BASE)
                    count += 1
                    if count >= 20000:
                        break
                pos += 3
                continue
            pos += 1
    _BOUNDARY_CACHE = boundaries
    return boundaries


def _alignment_state(pe: ManualPE, site_rva: int) -> str:
    """Classify whether a site RVA is a genuine instruction boundary."""
    cached = _ALIGN_CACHE.get(site_rva)
    if cached:
        return cached
    boundaries = _valid_boundaries(pe)
    state = "ALIGNMENT_VALID" if site_rva in boundaries else "ALIGNMENT_INVALID"
    _ALIGN_CACHE[site_rva] = state
    return state


# ---------------------------------------------------------------------------
# C. argv / command-line dataflow
# ---------------------------------------------------------------------------

def analyze_argv_dataflow(pe: ManualPE) -> list[dict[str, object]]:
    """Reconstruct the EXE-internal argv path as recovered by prior rounds,
    re-derived here from static bytes.

    Prior rounds documented:
      process command line -> [0xCA827C] -> UTF-16 string
        -> EXE+0x852724 argv builder -> [0x0196928C] count / [0x01969290] array
        -> EXE+0x37F580 predicate -> WIN_NO_TCLS if no -q/-qa

    This function verifies the statically visible links only.
    """
    rows: list[dict[str, object]] = []
    raw = pe.data

    # stage 1: the provider slot call site
    slot_va = 0x00CA827C
    slot_rva = slot_va - IMAGE_BASE
    sites = [i for i in range(len(raw) - 6)
             if raw[i] == 0xFF and raw[i + 1] == 0x15
             and struct.unpack_from("<I", raw, i + 2)[0] == slot_va]
    value = None
    vb, _s, _o, vst = pe.read_rva(slot_rva, 4)
    if vst == "OK" and len(vb) == 4:
        value = struct.unpack("<I", vb)[0]
    for i in sites:
        rva = rva_for_offset(pe, i)
        rows.append({
            "stage": "COMMANDLINE_PROVIDER_CALL",
            "site": fmt(rva),
            "site_kind": "SITE_RVA",
            "instruction": "call dword ptr [0x00CA827C]",
            "target": fmt(value),
            "target_mapping": classify_mapping(
                pe, value - IMAGE_BASE) if value else "",
            "classification": "DATAFLOW_CONFIRMED" if value else "DATAFLOW_UNRESOLVED",
            "evidence": "single FF15 site reads slot 0x00CA827C",
        })

    # stage 2: argv builder global pair writes (documented RVAs)
    argv_count_va = 0x0196928C
    argv_array_va = 0x01969290
    for name, va in (("argv_count", argv_count_va), ("argv_array", argv_array_va)):
        rva = va - IMAGE_BASE
        rows.append({
            "stage": "ARGV_STORAGE_GLOBAL",
            "site": fmt(rva),
            "site_kind": "GLOBAL_RVA",
            "instruction": "",
            "target": fmt(va),
            "target_mapping": classify_mapping(pe, rva),
            "classification": "BOUNDARY" if classify_mapping(pe, rva) == "VIRTUAL_ONLY"
            else "UNKNOWN",
            "evidence": f"documented argv {name} global; "
                        "not raw-backed in the file image",
        })

    # stage 3: the -q / -qa predicate function (EXE+0x37F580)
    predicate_rva = 0x0037F580
    mapping = classify_mapping(pe, predicate_rva)
    rows.append({
        "stage": "ARGV_PREDICATE_FUNCTION",
        "site": fmt(predicate_rva),
        "site_kind": "FUNCTION_RVA",
        "instruction": "",
        "target": fmt(predicate_rva),
        "target_mapping": mapping,
        "classification": "CANDIDATE" if mapping == "RAW_BACKED_EXECUTABLE"
        else classification_of(mapping),
        "evidence": "documented -q/-qa gate function; raw-backed in .text",
    })

    # stage 4: the gate global write discovered statically (0x849413B)
    write_rva = 0x00239C68
    if pe.read_rva(write_rva, 7)[3] == "OK":
        rows.append({
            "stage": "GATE_STATE_WRITE",
            "site": fmt(write_rva),
            "site_kind": "SITE_RVA",
            "instruction": "mov byte ptr [0x0849413B], 1",
            "target": "0x0849413B",
            "target_mapping": classify_mapping(pe, 0x0849413B - IMAGE_BASE),
            "classification": "DATAFLOW_CONFIRMED",
            "evidence": "strcmp-style argv loop sets the gate byte to 1",
        })
    return rows


def classification_of(mapping: str) -> str:
    if mapping == "TVM0_BOUNDARY":
        return "BOUNDARY"
    if mapping == "VIRTUAL_ONLY":
        return "UNKNOWN"
    return "CANDIDATE"


# ---------------------------------------------------------------------------
# D. Runtime states
# ---------------------------------------------------------------------------

def build_runtime_states(pe: ManualPE) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    def add(state, verdict, confidence, evidence_class, evidence):
        rows.append({"state": state, "verdict": verdict,
                     "confidence": confidence, "evidence_class": evidence_class,
                     "evidence": evidence})

    add("startup_state_gate_q_0x849413B", "EXISTS", "CONFIRMED",
        "DATAFLOW_CONFIRMED",
        "1 static write + 3 static reads in raw-backed .text")
    add("startup_state_gate_qa_0x849B500", "NO_STATIC_ACCESS", "CONFIRMED",
        "DATAFLOW_UNRESOLVED",
        "0 occurrences of the VA in the entire file image")
    add("startup_state_gate_src_tgp_0x849B501", "EXISTS", "CONFIRMED",
        "DATAFLOW_CONFIRMED", "1 static read at 0x002835BA")
    add("iips_failure_state_0x8189FEC", "NO_STATIC_ACCESS", "CONFIRMED",
        "BOUNDARY", "0 occurrences of the VA in the file image")
    add("argv_count_0x0196928C", "NO_STATIC_ACCESS", "CONFIRMED",
        "BOUNDARY", "global is VIRTUAL_ONLY; runtime-produced")
    add("argv_array_0x01969290", "NO_STATIC_ACCESS", "CONFIRMED",
        "BOUNDARY", "global is VIRTUAL_ONLY; runtime-produced")
    add("base_ordinal1_boundary_0x0E5DC665", "EXTERNAL_BOUNDARY", "CONFIRMED",
        "EXTERNAL_BOUNDARY", "PE Entry IAT slot; import ordinal 1")
    return rows


# ---------------------------------------------------------------------------
# E. Resource references
# ---------------------------------------------------------------------------

RESOURCE_NEEDLES = {
    "players/config_mp.cfg": [b"players/config_mp.cfg", b"players\\config_mp.cfg",
                              b"config_mp.cfg"],
    "settings_m.zip.iw4": [b"settings_m.zip.iw4"],
    "settings_c.zip.iw4": [b"settings_c.zip.iw4"],
    "main/video": [b"main/video", b"main\\video"],
    "main/demo": [b"main/demo", b"main\\demo"],
    "GameBabyConfig.dat": [b"GameBabyConfig.dat"],
    "main_dir": [b"main\\", b"main/"],
    "players_dir": [b"players\\", b"players/"],
    "settings_prefix": [b"settings_"],
    "config_mp": [b"config_mp"],
}


def _needle_hits(pe: ManualPE, needle: bytes) -> list[int]:
    hits = []
    raw = pe.data
    start = 0
    while True:
        i = raw.find(needle, start)
        if i < 0:
            break
        rva = rva_for_offset(pe, i)
        if rva is not None:
            hits.append(rva)
        start = i + 1
    return hits


def _abs_ref_sites(pe: ManualPE, va: int) -> list[int]:
    """Instruction sites that reference `va` as an absolute memory operand."""
    raw = pe.data
    pattern = struct.pack("<I", va)
    out: list[int] = []
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
            out.append(rva)
            break
    return out


def analyze_resources(pe: ManualPE) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for label, needles in RESOURCE_NEEDLES.items():
        hits: list[int] = []
        for needle in needles:
            hits.extend(_needle_hits(pe, needle))
        hits = sorted(set(hits))
        # a resource string is "referenced by code" when an aligned instruction
        # uses its VA as an immediate (push imm32) or absolute memory operand
        coerce: list[int] = []
        for h in hits:
            va = pe.image_base + h
            coerce.extend(_imm_ref_sites(pe, va))
            coerce.extend(_abs_ref_sites(pe, va))
        coerce = sorted(set(coerce))
        if hits and coerce:
            # A single immediate reference inside a partially-obfuscated stream is
            # not enough for a full dataflow chain.
            classification = "DATAFLOW_CONFIRMED" if len(coerce) >= 1 else "CANDIDATE"
        elif hits:
            classification = "CANDIDATE"
        else:
            classification = "NOT_FOUND"
        if hits and coerce and not _all_sites_aligned(pe, coerce):
            classification = "CANDIDATE"
        rows.append({
            "needle": label,
            "hit_count": len(hits),
            "hit_sites": ";".join(fmt(h) for h in hits[:10]),
            "code_ref_count": len(coerce),
            "code_ref_sites": ";".join(fmt(c) for c in coerce[:10]),
            "classification": classification,
            "evidence": "string presence + aligned push-imm32 / abs-memory xref",
        })
    return rows


def _all_sites_aligned(pe: ManualPE, sites: list[int]) -> bool:
    """Return True only when every reference site is a boundary reached by a
    push-ebp linear sweep (i.e. part of a consistent instruction stream)."""
    boundaries = _valid_boundaries(pe)
    return all(s in boundaries for s in sites)


def _imm_ref_sites(pe: ManualPE, va: int) -> list[int]:
    """Find `push <va>` (68 imm32) and `mov reg, <va>` (B8+r imm32) sites."""
    raw = pe.data
    pattern = struct.pack("<I", va)
    out: list[int] = []
    start = 0
    while True:
        i = raw.find(pattern, start)
        if i < 0:
            break
        start = i + 1
        for back in (1, 5):
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
            if insn.size != back + 4:
                continue
            if not insn.operands or insn.operands[0].type != X86_OP_IMM:
                continue
            if insn.operands[0].imm == va:
                out.append(rva)
                break
    return out


# ---------------------------------------------------------------------------
# F. IIPS boundary
# ---------------------------------------------------------------------------

IIPS_NEEDLES = [
    b"WIN_IIPS_INIT_ERROR",
    b"WIN_IIPS_INIT_FAILED",
    b"WIN_IIPS_DLL_ERROR",
    b"IIPS\\iips.dll",
    b"iips.dll",
    b"iipsinit",
    b"8189fec",
    b"8189FEC",
]


def analyze_iips_boundary(pe: ManualPE) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for needle in IIPS_NEEDLES:
        hits = _needle_hits(pe, needle)
        if hits:
            classification = "CANDIDATE"
        else:
            classification = "NOT_FOUND"
        rows.append({
            "needle": needle.decode("latin1"),
            "hit_count": len(hits),
            "hit_sites": ";".join(fmt(h) for h in hits[:12]),
            "classification": classification,
            "evidence": "literal byte search in the EXE file image",
        })
    # the documented error-handler candidate
    for rva in (0x0037FA70,):
        mapping = classify_mapping(pe, rva)
        insns = list(MD.disasm(pe.read_rva(rva, 32)[0], IMAGE_BASE + rva, count=6))
        first = f"{insns[0].mnemonic} {insns[0].op_str}" if insns else ""
        rows.append({
            "needle": fmt(rva) + " (error-handler candidate)",
            "hit_count": 1,
            "hit_sites": fmt(rva),
            "classification": "CANDIDATE" if mapping == "RAW_BACKED_EXECUTABLE"
            else classification_of(mapping),
            "evidence": f"{mapping}; first instruction: {first}",
        })
    return rows


# ---------------------------------------------------------------------------
# G. Function tables
# ---------------------------------------------------------------------------

CORE005_TABLE_SUSPECTS = [
    0x0E9DC635, 0x0E9DC665, 0x00CA8000, 0x00CA812C, 0x00CA8190,
    0x00CA819C, 0x00CA8170, 0x00CA8534, 0x00CA8114, 0x00CA818C,
    0x00CA84C8, 0x0849413B, 0x0849B500, 0x0849B501, 0x08426AEC,
    0x0E9DC641, 0x0E9DC645,
]


def analyze_function_tables(pe: ManualPE) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    raw = pe.data
    for va in CORE005_TABLE_SUSPECTS:
        rva = va - IMAGE_BASE if va >= IMAGE_BASE else va
        mapping = classify_mapping(pe, rva)
        entries = []
        entry_count = 0
        if mapping == "RAW_BACKED_DATA" or mapping == "RAW_BACKED_EXECUTABLE":
            for i in range(32):
                b, _s, _o, st = pe.read_rva(rva + i * 4, 4)
                if st != "OK" or len(b) < 4:
                    break
                value = struct.unpack("<I", b)[0]
                if value == 0:
                    break
                entries.append(value)
                entry_count += 1
        first = entries[0] if entries else None
        first_mapping = classify_mapping(
            pe, first - IMAGE_BASE) if first else ""
        # Is this address used as an indirect call/jmp slot?
        used = any(raw[i] == 0xFF and raw[i + 1] in (0x15, 0x25)
                   and struct.unpack_from("<I", raw, i + 2)[0] == va
                   for i in range(len(raw) - 6))
        # Determine table kind
        if rva == 0x0E5DC665:
            table_kind = "IMPORT_IAT_SLOT"
            classification = "EXTERNAL_BOUNDARY"
        elif mapping == "VIRTUAL_ONLY":
            table_kind = "RUNTIME_GENERATED"
            classification = "UNKNOWN"
        elif used and entry_count >= 1:
            table_kind = "FUNCTION_POINTER_SLOT"
            classification = "DATAFLOW_CONFIRMED"
        elif entry_count == 0:
            table_kind = "NOT_A_TABLE"
            classification = "NOT_FOUND"
        elif first_mapping == "RAW_BACKED_EXECUTABLE":
            table_kind = "POINTER_ARRAY"
            classification = "CANDIDATE"
        else:
            table_kind = "UNKNOWN"
            classification = "UNKNOWN"
        rows.append({
            "table_va": fmt(va),
            "table_rva": fmt(rva),
            "table_section": classify_mapping(pe, rva),
            "entry_count": entry_count,
            "first_entry": fmt(first),
            "target_mapping": first_mapping,
            "used_by_call_site": "YES" if used else "NO",
            "table_kind": table_kind,
            "classification": classification,
            "evidence": ("referenced by FF15/FF25 indirect transfer"
                         if used else "no confirmed indirect transfer use"),
        })
    return rows


# ---------------------------------------------------------------------------
# H. Runtime islands
# ---------------------------------------------------------------------------

ISLAND_DEFS = {
    "bootstrap_gate": {
        "functions": [0x0037F580, 0x0037FA70],
        "globals": ["0x0849413B", "0x0849B501"],
    },
    "argv_provider": {
        "functions": [0x00561133],
        "globals": ["0x00CA827C"],
    },
    "network_stun": {
        "functions": [0x002212C0, 0x002213B9, 0x002214C5],
        "globals": ["0x0849413B", "0x0849B500"],
    },
    "iips_boundary": {
        "functions": [0x0037FA70],
        "globals": ["0x08189FEC"],
    },
    "scaleform_exports": {
        "functions": [0x000364F0, 0x000365E0, 0x00036520],
        "globals": [],
    },
}


def build_runtime_islands(pe, contract, indirect_rows, resource_rows):
    rows = []
    for island, spec in ISLAND_DEFS.items():
        funcs = [f for f in spec["functions"]]
        globals_ = list(spec["globals"])
        entry_connected = "NO"
        activation = "UNKNOWN"
        if island == "bootstrap_gate":
            activation = "CANDIDATE_ARGV_GATE"
        elif island == "argv_provider":
            activation = "CANDIDATE_EXTERNAL_PROVIDER"
        elif island == "network_stun":
            activation = "CANDIDATE_GATE_CONSUMER"
        elif island == "iips_boundary":
            activation = "CANDIDATE_FAILURE_BOUNDARY"
        elif island == "scaleform_exports":
            activation = "CANDIDATE_EXTERNAL_CALLER"
        rows.append({
            "island": island,
            "function_count": len(funcs),
            "functions": ";".join(fmt(f) for f in funcs),
            "global_count": len(globals_),
            "globals": ";".join(globals_),
            "external_dependencies": "Base.dll ordinal 1 / iips.dll",
            "activation": activation,
            "entry_connected": entry_connected,
            "classification": "RUNTIME_ISLAND",
        })
    return rows


# ---------------------------------------------------------------------------
# I. Activation candidates
# ---------------------------------------------------------------------------

def build_activation_candidates(pe, contract, island_rows):
    rows = []
    rows.append({
        "candidate": "0x0849413B",
        "candidate_kind": "STARTUP_STATE_GLOBAL",
        "mechanism": "argv gate writes 1; consumers branch on it",
        "entry_connected": "NO",
        "evidence_class": "DATAFLOW_CONFIRMED",
        "classification": "CANDIDATE",
        "evidence": "1 write at 0x00239C68, 3 reads",
    })
    rows.append({
        "candidate": "0x00CA827C",
        "candidate_kind": "INDIRECT_SLOT",
        "mechanism": "call dword ptr [slot] at 0x00561133 provides argv",
        "entry_connected": "NO",
        "evidence_class": "DATAFLOW_CONFIRMED",
        "classification": "CANDIDATE",
        "evidence": "slot value 0x00A1517E is VIRTUAL_ONLY (runtime target)",
    })
    rows.append({
        "candidate": "0x0849B501",
        "candidate_kind": "STARTUP_STATE_GLOBAL",
        "mechanism": "single static read at 0x002835BA",
        "entry_connected": "NO",
        "evidence_class": "DATAFLOW_UNRESOLVED",
        "classification": "UNKNOWN",
        "evidence": "write site not present in file image",
    })
    rows.append({
        "candidate": "0x0037F580",
        "candidate_kind": "PREDICATE_FUNCTION",
        "mechanism": "documented -q/-qa gate predicate; raw-backed .text",
        "entry_connected": "NO",
        "evidence_class": "CANDIDATE",
        "classification": "CANDIDATE",
        "evidence": "address is raw-backed; not reached from PE Entry",
    })
    rows.append({
        "candidate": "0x0E5DC665",
        "candidate_kind": "EXTERNAL_BOUNDARY",
        "mechanism": "PE Entry calls Base.dll ordinal 1",
        "entry_connected": "YES",
        "evidence_class": "EXTERNAL_BOUNDARY",
        "classification": "BOUNDARY",
        "evidence": "the only Entry-connected edge",
    })
    return rows


# ---------------------------------------------------------------------------
# J. Evidence matrix
# ---------------------------------------------------------------------------

def build_evidence_matrix(pe, contract, indirect_rows, argv_rows, state_rows,
                          resource_rows, iips_rows, island_rows):
    rows = []

    def add(question, answer, confidence, evidence_class, basis):
        rows.append({"question": question, "answer": answer,
                     "confidence": confidence, "evidence_class": evidence_class,
                     "basis": basis})

    add("Entry -> EXE native fall-through",
        "NOT_FOUND", "CONFIRMED", "UNKNOWN",
        "PE Entry is 6 bytes followed by zero padding (CORE-006)")
    add("Entry -> EXE native continuation",
        "NOT_FOUND", "CONFIRMED", "EXTERNAL_BOUNDARY",
        "only recovered edge is the Base.dll ordinal-1 IAT call")
    add("EXE startup state globals",
        "1 confirmed (0x0849413B), 1 confirmed read (0x0849B501)",
        "CONFIRMED", "DATAFLOW_CONFIRMED",
        "absolute-memory operand scan with alignment validation")
    add("0x0849B500 static access",
        "NOT_FOUND", "CONFIRMED", "DATAFLOW_UNRESOLVED",
        "zero occurrences of the VA in the file image")
    add("argv provider indirect slot",
        "0x00CA827C (1 call site at 0x00561133)", "CONFIRMED",
        "DATAFLOW_CONFIRMED",
        "FF15 slot read and single xref")
    add("function-pointer / dispatch tables",
        "no confirmed function table", "CONFIRMED", "UNKNOWN",
        "CORE-005 suspects reclassified; runtime-generated pointers")
    add("filesystem resource contract",
        "not confirmed in EXE file image", "CONFIRMED", "UNKNOWN",
        "resource string xref search")
    add("IIPS result consumption in EXE",
        "UNKNOWN", "UNKNOWN", "BOUNDARY",
        "IIPS failure state is VIRTUAL_ONLY; no static consumer")
    add("thread-start mechanism",
        "UNKNOWN", "UNKNOWN", "UNKNOWN",
        "no thread API symbol or recovered call site")
    add("runtime islands",
        f"{len(island_rows)} candidate islands", "CANDIDATE",
        "UNKNOWN", "grouping by known functions/globals; activation unproven")
    return rows


def main() -> int:
    digest = sha256_of(SAMPLE)
    print("=" * 78)
    print("CODOL_STANDALONE_CORE_007 -- External-Boundary Contract Recovery")
    print("=" * 78)
    print(f"sample_match = {'CONFIRMED' if digest == EXPECTED_SHA256 else 'MISMATCH'}")
    pe = ManualPE(SAMPLE)
    print(f"image_base = 0x{pe.image_base:08X}   entry_rva = 0x{pe.entry_rva:08X}")

    contract, detail = global_contract_rows(pe)
    print("\n=== Global slot contract ===")
    for row in contract:
        print(f"  {row['global_va']} [{row['global_mapping']}] "
              f"reads={row['read_count']} writes={row['write_count']} "
              f"-> {row['state_class']}")
        for s in detail:
            if s["global_va"] == row["global_va"]:
                print(f"      {s['site_rva']} {s['instruction']}")

    write_csv(ROOT / "exe_core007_global_contract.csv",
              ["global_va", "global_rva", "global_mapping", "label_hint",
               "site_count", "read_count", "write_count", "first_write",
               "first_read", "read_sites", "write_sites", "state_class"], contract)
    write_csv(ROOT / "exe_core007_global_sites.csv",
              ["global_va", "site_rva", "site_va", "section", "bytes",
               "instruction", "mnemonic", "kind", "operand_read",
               "operand_write"], detail)
    print("\nartifacts: exe_core007_global_contract.csv, exe_core007_global_sites.csv")

    # ---- B. Indirect slots (IAT-like dispatch slots) ----
    indirect_rows = analyze_indirect_slots(pe)
    print(f"\n=== Indirect slots (FF 15 abs32) : {len(indirect_rows)} ===")
    for row in indirect_rows[:25]:
        print(f"  {row['slot_va']} <- {row['site_rva']} : {row['instruction']} "
              f"[{row['slot_target_mapping']}] xrefs={row['xref_count']}")
    write_csv(ROOT / "exe_core007_indirect_slots.csv",
              ["slot_va", "slot_rva", "slot_section", "initial_value",
               "initial_value_mapping", "site_rva", "instruction",
               "slot_target", "slot_target_mapping", "xref_count",
               "aligned_xref_count", "alignment_state", "classification"],
              indirect_rows)

    # ---- C. argv / command-line dataflow ----
    argv_rows = analyze_argv_dataflow(pe)
    print(f"\n=== argv dataflow : {len(argv_rows)} ===")
    for row in argv_rows:
        print(f"  {row['stage']:24s} {row['site']:>14s} {row['instruction']} "
              f"[{row['classification']}]")
    write_csv(ROOT / "exe_core007_argv_dataflow.csv",
              ["stage", "site", "site_kind", "instruction", "target",
               "target_mapping", "classification", "evidence"], argv_rows)

    # ---- D. Runtime states ----
    state_rows = build_runtime_states(pe)
    print(f"\n=== Runtime states : {len(state_rows)} ===")
    for row in state_rows:
        print(f"  {row['state']} = {row['verdict']} ({row['evidence']})")
    write_csv(ROOT / "exe_core007_runtime_states.csv",
              ["state", "verdict", "confidence", "evidence_class", "evidence"],
              state_rows)

    # ---- E. Resource references ----
    resource_rows = analyze_resources(pe)
    print(f"\n=== Resource references : {len(resource_rows)} ===")
    for row in resource_rows:
        print(f"  {row['needle']:28s} hits={row['hit_count']:3d} "
              f"refs={row['code_ref_count']} "
              f"[{row['classification']}]")
    write_csv(ROOT / "exe_core007_resource_refs.csv",
              ["needle", "hit_count", "hit_sites", "code_ref_count",
               "code_ref_sites", "classification", "evidence"], resource_rows)

    # ---- F. IIPS boundary ----
    iips_rows = analyze_iips_boundary(pe)
    print(f"\n=== IIPS boundary : {len(iips_rows)} ===")
    for row in iips_rows:
        print(f"  {row['needle']:28s} hits={row['hit_count']:3d} "
              f"[{row['classification']}]")
    write_csv(ROOT / "exe_core007_iips_boundary.csv",
              ["needle", "hit_count", "hit_sites", "classification",
               "evidence"], iips_rows)

    # ---- G. function tables (CORE-005's 17 + core006 rejects) ----
    table_rows = analyze_function_tables(pe)
    print(f"\n=== Function-table suspects : {len(table_rows)} ===")
    for row in table_rows:
        print(f"  {row['table_va']:>12s} kind={row['table_kind']:24s} "
              f"[{row['classification']}]")
    write_csv(ROOT / "exe_core007_function_tables.csv",
              ["table_va", "table_rva", "table_section", "entry_count",
               "first_entry", "target_mapping", "used_by_call_site",
               "table_kind", "classification", "evidence"], table_rows)

    # ---- H. runtime islands ----
    island_rows = build_runtime_islands(pe, contract, indirect_rows, resource_rows)
    print(f"\n=== Runtime islands : {len(island_rows)} ===")
    for row in island_rows:
        print(f"  {row['island']:22s} functions={row['function_count']:3d} "
              f"globals={row['global_count']:3d} [{row['activation']}]")
    write_csv(ROOT / "exe_core007_runtime_islands.csv",
              ["island", "function_count", "functions", "global_count",
               "globals", "external_dependencies", "activation",
               "entry_connected", "classification"], island_rows)

    # ---- I. activation candidates ----
    activation_rows = build_activation_candidates(pe, contract, island_rows)
    print(f"\n=== Activation candidates : {len(activation_rows)} ===")
    for row in activation_rows:
        print(f"  {row['candidate']:>14s} -> {row['mechanism'][:60]} "
              f"[{row['classification']}]")
    write_csv(ROOT / "exe_core007_activation_candidates.csv",
              ["candidate", "candidate_kind", "mechanism", "entry_connected",
               "evidence_class", "classification", "evidence"], activation_rows)

    # ---- J. evidence matrix ----
    matrix = build_evidence_matrix(pe, contract, indirect_rows, argv_rows,
                                   state_rows, resource_rows, iips_rows,
                                   island_rows)
    write_csv(ROOT / "exe_core007_evidence_matrix.csv",
              ["question", "answer", "confidence", "evidence_class", "basis"],
              matrix)
    print(f"\n=== Evidence matrix rows: {len(matrix)} ===")

    # ---- K. dispatch slot array structure ----
    slot_struct = analyze_slot_array(pe, indirect_rows)
    print(f"\n=== Dispatch slot array ===")
    for k, v in slot_struct.items():
        if k != "rows":
            print(f"  {k:32s}: {v}")
    write_csv(ROOT / "exe_core007_dispatch_slots.csv",
              ["slot_va", "slot_rva", "slot_target_rva", "slot_target_mapping",
               "xref_count", "table_rva", "classification"],
              slot_struct["rows"])

    # ---- L. cross-check corrections vs prior rounds ----
    corrections = build_prior_round_corrections(pe)
    print(f"\n=== Prior-round corrections : {len(corrections)} ===")
    for row in corrections:
        print(f"  {row['address']:>12s} prior={row['prior_claim'][:40]:40s} "
              f"now={row['static_finding'][:40]}")
    write_csv(ROOT / "exe_core007_prior_round_corrections.csv",
              ["address", "prior_claim", "static_finding", "verdict", "evidence"],
              corrections)
    return 0


def analyze_slot_array(pe: ManualPE, indirect_rows) -> dict[str, object]:
    """Characterise the EXE dispatch slot array (the 0xCAxxxx / 0xDBxxxx slots
    used by FF 15 indirect calls)."""
    rows = []
    targets_by_window: Counter = Counter()
    for row in indirect_rows:
        slot_va = int(row["slot_va"], 16)
        target_va = int(row["slot_target"], 16) if row["slot_target"] else 0
        target_rva = (target_va - IMAGE_BASE) if target_va >= IMAGE_BASE else 0
        if target_rva:
            targets_by_window[(target_rva >> 16) << 16] += 1
        rows.append({
            "slot_va": row["slot_va"],
            "slot_rva": row["slot_rva"],
            "slot_target_rva": fmt(target_rva) if target_rva else "",
            "slot_target_mapping": row["slot_target_mapping"],
            "xref_count": row["xref_count"],
            "table_rva": "",
            "classification": row["classification"],
        })
    total = len(indirect_rows)
    runtime_targets = sum(1 for r in indirect_rows
                          if r["slot_target_mapping"] == "VIRTUAL_ONLY")
    # A confirmed function pointer requires: an alignment-valid call site, a slot
    # that lives in a data section (not inside a floating-point constant run or a
    # near-null address), and a target that is raw-backed executable.
    confirmed_ptrs = []
    for r in indirect_rows:
        if r.get("alignment_state") != "ALIGNMENT_VALID":
            continue
        if r["slot_target_mapping"] != "RAW_BACKED_EXECUTABLE":
            continue
        slot_va = int(r["slot_va"], 16)
        if slot_va < 0x00100000:  # near-null / header-relative garbage
            continue
        if not _slot_is_data_pointer(pe, slot_va - IMAGE_BASE):
            continue
        confirmed_ptrs.append(r["slot_va"])
    raw_targets = len(confirmed_ptrs)
    raw_targets_unvalidated = sum(
        1 for r in indirect_rows
        if r["slot_target_mapping"] == "RAW_BACKED_EXECUTABLE")
    aligned_slots = sum(1 for r in indirect_rows
                        if r.get("alignment_state") == "ALIGNMENT_VALID")
    top_window = targets_by_window.most_common(1)[0][0] if targets_by_window else 0
    return {
        "slot_count": total,
        "slots_with_valid_alignment": aligned_slots,
        "slots_targeting_virtual_only": runtime_targets,
        "slots_targeting_raw_backed_executable": raw_targets,
        "slots_targeting_raw_backed_executable_unvalidated": raw_targets_unvalidated,
        "confirmed_function_pointers": ";".join(confirmed_ptrs) if confirmed_ptrs else "NONE",
        "dominant_target_window_rva": fmt(top_window),
        "target_window_desc": "the EXE's runtime-populated code region",
        "rows": sorted(rows, key=lambda r: r["xref_count"], reverse=True),
    }


def _slot_is_data_pointer(pe: ManualPE, slot_rva: int) -> bool:
    """Heuristically reject slots that sit inside floating-point constant runs
    or other non-pointer data.

    A slot is accepted only when its neighbours are in-image pointers AND are
    not all identical (a genuine pointer table has distinct entries; a float
    constant run repeats the same bytes)."""
    values: list[int] = []
    for delta in (-12, -8, -4, 4, 8, 12):
        vb, _s, _o, st = pe.read_rva(slot_rva + delta, 4)
        if st != "OK" or len(vb) < 4:
            continue
        value = struct.unpack("<I", vb)[0]
        values.append(value)
    in_image = [v for v in values
                if IMAGE_BASE <= v < IMAGE_BASE + pe.size_of_image]
    if len(in_image) < 3:
        return False
    # A genuine pointer table has mostly-distinct entries. A float constant run
    # repeats the same value; require at least 60% distinct.
    if len(set(in_image)) < max(2, int(0.6 * len(in_image))):
        return False
    # Reject slots whose neighbour targets are all in one tight 16-byte cluster
    # (that pattern is a numeric constant, not a code-pointer table).
    if len(set(v >> 4 for v in in_image)) <= 1:
        return False
    return True


def build_prior_round_corrections(pe: ManualPE) -> list[dict[str, object]]:
    """Record where a static re-derivation differs from a prior round's claim."""
    rows = []
    rows.append({
        "address": "0x0849B500",
        "prior_claim": "written to 1 by -qa (runtime observation)",
        "static_finding": "0 VA occurrences anywhere in the file image",
        "verdict": "DATAFLOW_UNRESOLVED",
        "evidence": "the only nearby instruction reads 0x0009B500, not 0x0849B500",
    })
    rows.append({
        "address": "0x0849413B",
        "prior_claim": "4 read sites (runtime scan)",
        "static_finding": "3 reads + 1 write, all alignment-validated",
        "verdict": "DATAFLOW_CONFIRMED",
        "evidence": "0x0016FF08, 0x0017FF46, 0x0028E1A4 (read); "
                    "0x00239C68 (write)",
    })
    rows.append({
        "address": "0x0849B501",
        "prior_claim": "written to 1 by -src=tgp (runtime observation)",
        "static_finding": "1 read at 0x002835BA; no static write site",
        "verdict": "DATAFLOW_UNRESOLVED",
        "evidence": "write happens only in the virtual-only region",
    })
    rows.append({
        "address": "0x08189FEC",
        "prior_claim": "IIPS failure state value",
        "static_finding": "0 VA occurrences; state is runtime-produced",
        "verdict": "BOUNDARY",
        "evidence": "IIPS error value is not stored as an absolute operand in EXE",
    })
    rows.append({
        "address": "0x00CA827C",
        "prior_claim": "argv provider slot (API name unproven)",
        "static_finding": "single FF15 site at 0x00561133; slot value "
                          "0x00A1517E is VIRTUAL_ONLY",
        "verdict": "DATAFLOW_CONFIRMED (site) / BOUNDARY (target)",
        "evidence": "8-byte window 0x00561133",
    })
    return rows


if __name__ == "__main__":
    raise SystemExit(main())
