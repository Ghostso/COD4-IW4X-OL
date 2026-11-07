from __future__ import annotations

"""
EXE-CORE-006: Entry-connected Native Bootstrap Recovery

Scope: codoMP_client_shipRetail.exe only.
Other DLLs appear only as external boundaries; their internals are not analyzed.

Goal: prove or disprove that a real, evidence-backed execution path exists from
the PE Entry point into EXE-native initialization code.

Prohibited: WeGame, Sandboxie, Procmon, Tencent launcher reversing, TCLS internals,
Base.dll internals, TenProxy.dll internals, .tvm0 semantic guessing, CODOL-MP.exe
re-audit, modifying EXE/DLL, patch, hook, debugger-dependent conclusions.

Allowed: static PE analysis, RVA->file offset, x86 disassembly, direct CALL/JMP,
indirect-call analysis, function pointer analysis, table analysis, thread seed
analysis, CFG recovery, data flow analysis.
"""

import csv
import hashlib
import struct
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import capstone
from capstone import CS_ARCH_X86, CS_GRP_CALL, CS_GRP_JUMP, CS_GRP_RET, CS_MODE_32
from capstone.x86_const import (
    X86_OP_IMM,
    X86_OP_MEM,
    X86_OP_REG,
    X86_REG_EAX,
    X86_REG_EBX,
    X86_REG_ECX,
    X86_REG_EDX,
    X86_REG_ESI,
    X86_REG_EDI,
    X86_REG_EBP,
    X86_REG_ESP,
)

from core004a_diagnostic import ManualPE, SAMPLE


ROOT = Path(__file__).resolve().parent
EXPECTED_SHA256 = "36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537"
EXPECTED_IMAGE_BASE = 0x00400000
EXPECTED_ENTRY_RVA = 0x0E5DC690

TVM0_NAME = ".tvm0"

# Historical native bootstrap candidates carried over from EXE-CORE-005.
HISTORICAL_BOOTSTRAP_CANDIDATES = [
    0x0077F580,
    0x0077F8B3,
    0x004FD9B0,
    0x004FCEE0,
    0x00808650,
    0x007E98F0,
    0x006212C0,
]

# EXE-internal 0xCAxxxx slots flagged by CORE-005 as indirect-call sites.
CORE005_INTERNAL_SLOTS = [
    0x00CA812C,
    0x00CA8190,
    0x00CA819C,
    0x00CA84C8,
]

MAX_FUNCTIONS = 256
MAX_BLOCKS = 6000
MAX_INSTRUCTIONS_PER_BLOCK = 512


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


def fmt_rva(value: int | None) -> str:
    if value is None:
        return ""
    if value < 0:
        return f"-0x{-value:08X}"
    return f"0x{value:08X}"


def map_status(pe: ManualPE, rva: int) -> tuple[str, str, int | None]:
    """Return (status, section_name, file_offset) with explicit boundary states."""
    section, offset, status = pe.rva_to_offset(rva)
    if section is None and status == "PE_HEADERS":
        return "PE_HEADERS", "", offset
    if section is None:
        return status, "", None
    if section.name == TVM0_NAME:
        return "TVM0_BOUNDARY", section.name, offset if status == "OK" else None
    if status == "VIRTUAL_ONLY":
        return "VIRTUAL_ONLY", section.name, None
    if status != "OK":
        return status, section.name, None
    return ("RAW_BACKED_EXECUTABLE" if section.executable else "RAW_BACKED_DATA",
            section.name, offset)


def relative_target(insn) -> int | None:
    raw = bytes(insn.bytes)
    if not raw:
        return None
    disp: int | None = None
    if raw[0] in (0xE8, 0xE9) and len(raw) >= 5:
        disp = struct.unpack_from("<i", raw, 1)[0]
    elif raw[0] == 0xEB and len(raw) >= 2:
        disp = struct.unpack_from("<b", raw, 1)[0]
    elif 0x70 <= raw[0] <= 0x7F and len(raw) >= 2:
        disp = struct.unpack_from("<b", raw, 1)[0]
    elif raw[0] == 0x0F and len(raw) >= 6 and 0x80 <= raw[1] <= 0x8F:
        disp = struct.unpack_from("<i", raw, 2)[0]
    if disp is None:
        return None
    return (insn.address + insn.size + disp) & 0xFFFFFFFF


# ---------------------------------------------------------------------------
# 1. Entry / import / export / TLS structural analysis
# ---------------------------------------------------------------------------

def analyze_entry(pe: ManualPE) -> dict[str, object]:
    rva = pe.entry_rva
    data, section, off, status = pe.read_rva(rva, 32)
    md = capstone.Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    insns = list(md.disasm(data, pe.image_base + rva))
    entry_text = f"{insns[0].mnemonic} {insns[0].op_str}" if insns else ""
    # bytes after the entry instruction
    after = b""
    if off is not None:
        after = pe.data[off + insns[0].size: off + 4096] if insns else b""
    trailing_zeros = 0
    for b in after:
        if b == 0:
            trailing_zeros += 1
        else:
            break
    return {
        "entry_rva": rva,
        "entry_va": pe.image_base + rva,
        "section": section.name if section else "",
        "file_offset": off,
        "bytes": data[:8].hex(" ").upper(),
        "decoded": entry_text,
        "instruction_size": insns[0].size if insns else 0,
        "trailing_zero_bytes_after_entry": trailing_zeros,
    }


def parse_imports(pe: ManualPE) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    dd = pe.pe_offset + 4 + 20 + 96
    import_rva = struct.unpack_from("<I", pe.data, dd + 8)[0]
    if not import_rva:
        return rows
    for i in range(64):
        b, sec, off, st = pe.read_rva(import_rva + i * 20, 20)
        if st != "OK" or len(b) < 20:
            break
        oft, ts, fc, name_rva, first_thunk = struct.unpack("<IIIII", b)
        if oft == 0 and name_rva == 0 and first_thunk == 0:
            break
        nb, _, _, nst = pe.read_rva(name_rva, 256)
        dll = nb.split(b"\0")[0].decode("latin1", "replace") if nst == "OK" else ""
        thunk_rva = oft or first_thunk
        for j in range(4096):
            tb, _, _, tst = pe.read_rva(thunk_rva + j * 4, 4)
            if tst != "OK" or len(tb) < 4:
                break
            value = struct.unpack("<I", tb)[0]
            if value == 0:
                break
            is_ordinal = bool(value & 0x80000000)
            rows.append({
                "descriptor_index": i,
                "dll": dll,
                "dll_name_rva": fmt_rva(name_rva),
                "oft_rva": fmt_rva(oft),
                "first_thunk_rva": fmt_rva(first_thunk),
                "iat_slot_rva": fmt_rva(first_thunk + j * 4),
                "int_slot_rva": fmt_rva(thunk_rva + j * 4),
                "thunk_index": j,
                "thunk_value": fmt_rva(value),
                "import_kind": "ORDINAL" if is_ordinal else "NAME",
                "ordinal": (value & 0xFFFF) if is_ordinal else "",
                "hint_name_rva": fmt_rva(value) if not is_ordinal else "",
            })
    return rows


def parse_exports(pe: ManualPE) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    dd = pe.pe_offset + 4 + 20 + 96
    export_rva, export_size = struct.unpack_from("<II", pe.data, dd)
    if not export_rva:
        return rows
    b, _, _, st = pe.read_rva(export_rva, 0x28)
    if st != "OK" or len(b) < 0x28:
        return rows
    (_char, _ts, _maj, _min, name_rva, ord_base, n_func, n_name,
     addr_func, addr_name, addr_ord) = struct.unpack("<IIHHIIIIIII", b)
    dll_name = ""
    nb, _, _, nst = pe.read_rva(name_rva, 128)
    if nst == "OK":
        dll_name = nb.split(b"\0")[0].decode("latin1", "replace")
    funcs: list[int | None] = []
    for i in range(n_func):
        fb, _, _, fst = pe.read_rva(addr_func + i * 4, 4)
        funcs.append(struct.unpack("<I", fb)[0] if fst == "OK" and len(fb) == 4 else None)
    by_index: dict[int, list[str]] = defaultdict(list)
    index_of: dict[int, int] = {}
    ordered = []
    for i in range(n_name):
        ob, _, _, _ = pe.read_rva(addr_ord + i * 2, 2)
        o = struct.unpack("<H", ob)[0]
        nb2, _, _, _ = pe.read_rva(addr_name + i * 4, 4)
        nrva = struct.unpack("<I", nb2)[0]
        sb, _, _, _ = pe.read_rva(nrva, 256)
        nm = sb.split(b"\0")[0].decode("latin1", "replace")
        by_index[o].append(nm)
        index_of[i] = o
        ordered.append((o, nm, nrva))
    for o, nm, nrva in sorted(ordered):
        target = funcs[o] if o < len(funcs) else None
        rows.append({
            "dll": dll_name,
            "ordinal": ord_base + o,
            "index": o,
            "function_rva": fmt_rva(target),
            "name_rva": fmt_rva(nrva),
            "name": nm,
            "mapping_status": map_status(pe, target)[0] if target else "UNKNOWN",
        })
    return rows


def analyze_tls(pe: ManualPE) -> dict[str, object]:
    dd = pe.pe_offset + 4 + 20 + 96
    tls_rva, tls_size = struct.unpack_from("<II", pe.data, dd + 9 * 8)
    result: dict[str, object] = {
        "tls_rva": fmt_rva(tls_rva), "tls_size": fmt_rva(tls_size),
        "status": "NOT_PRESENT", "callbacks": [],
    }
    if not tls_rva:
        return result
    b, _, _, st = pe.read_rva(tls_rva, 0x18)
    if st != "OK" or len(b) < 0x18:
        result["status"] = "UNREADABLE"
        return result
    start, end, index_va, callbacks_va, zero_fill, chars = struct.unpack("<IIIIII", b)
    result.update({
        "status": "PRESENT",
        "start_raw_va": fmt_rva(start), "end_raw_va": fmt_rva(end),
        "index_va": fmt_rva(index_va), "callbacks_va": fmt_rva(callbacks_va),
        "zero_fill": fmt_rva(zero_fill), "characteristics": fmt_rva(chars),
    })
    if callbacks_va:
        cb_rva = callbacks_va - pe.image_base
        cbs = []
        for i in range(64):
            cb, _, _, cst = pe.read_rva(cb_rva + i * 4, 4)
            if cst != "OK" or len(cb) < 4:
                break
            v = struct.unpack("<I", cb)[0]
            if v == 0:
                break
            cbs.append(fmt_rva(v))
        result["callbacks"] = cbs
        result["callback_count"] = len(cbs)
    return result


# ---------------------------------------------------------------------------
# 2. Entry-connected CFG (direct + indirect-slot analysis)
# ---------------------------------------------------------------------------

@dataclass
class Insn:
    rva: int
    size: int
    mnemonic: str
    op_str: str
    raw: bytes
    groups: frozenset[int]
    operands: tuple = ()

    @property
    def end(self) -> int:
        return self.rva + self.size


@dataclass
class Block:
    rva: int
    function_rva: int
    insns: list[Insn] = field(default_factory=list)
    terminator: str = ""


class EntryConnectedCFG:
    """Recursive-descent CFG rooted strictly at the PE Entry point."""

    def __init__(self, pe: ManualPE):
        self.pe = pe
        self.md = capstone.Cs(CS_ARCH_X86, CS_MODE_32)
        self.md.detail = True
        self.blocks: dict[int, Block] = {}
        self.edges: list[dict[str, object]] = []
        self.decode_failures: list[dict[str, object]] = []
        self.indirect_sites: list[dict[str, object]] = []
        self._edge_keys: set[tuple] = set()
        # register value tracking for simple "call [reg]" resolution is not
        # attempted unless a concrete memory/absolute operand is present.

    def disasm_at(self, rva: int, max_count: int) -> list[Insn]:
        data, section, off, status = self.pe.read_rva(rva, max_count * 15 + 16)
        if status != "OK" or section is None or not section.executable:
            return []
        out: list[Insn] = []
        for insn in self.md.disasm(data, self.pe.image_base + rva, count=max_count):
            out.append(Insn(
                rva=insn.address - self.pe.image_base,
                size=insn.size,
                mnemonic=insn.mnemonic,
                op_str=insn.op_str,
                raw=bytes(insn.bytes),
                groups=frozenset(insn.groups),
                operands=tuple(insn.operands),
            ))
        return out

    def add_edge(self, src_block: int, src_insn: int, etype: str, dst: int | None,
                 target_kind: str, confidence: str, evidence: str) -> None:
        key = (src_block, src_insn, etype, dst)
        if key in self._edge_keys:
            return
        self._edge_keys.add(key)
        self.edges.append({
            "source_block": fmt_rva(src_block),
            "instruction_rva": fmt_rva(src_insn),
            "edge_type": etype,
            "target_rva": fmt_rva(dst) if dst is not None else "",
            "target_kind": target_kind,
            "confidence": confidence,
            "evidence": evidence,
        })

    def analyze(self) -> None:
        start = self.pe.entry_rva
        queue: list[int] = [start]
        seen: set[int] = set()
        while queue and len(self.blocks) < MAX_BLOCKS:
            block_rva = queue.pop(0)
            if block_rva in seen:
                continue
            if map_status(self.pe, block_rva)[0] != "RAW_BACKED_EXECUTABLE":
                continue
            seen.add(block_rva)
            block = Block(rva=block_rva, function_rva=start)
            self.blocks[block_rva] = block
            insns = self.disasm_at(block_rva, MAX_INSTRUCTIONS_PER_BLOCK)
            if not insns:
                self.decode_failures.append({
                    "rva": fmt_rva(block_rva), "reason": "NO_INSTRUCTION_DECODED",
                })
                continue
            for insn in insns:
                block.insns.append(insn)
                if insn.size == 0:
                    block.terminator = "ZERO_SIZE"
                    break
                # zero padding -> stop
                if insn.raw == b"\x00" and insn.mnemonic == "add" and insn.op_str == "byte ptr [eax], al":
                    block.terminator = "ZERO_PADDING"
                    break
                is_call = CS_GRP_CALL in insn.groups
                is_jump = CS_GRP_JUMP in insn.groups
                is_ret = CS_GRP_RET in insn.groups
                if is_call:
                    self.handle_transfer(block, insn, "CALL", queue)
                    # a CALL falls through to the next instruction on return
                    fall = insn.end
                    fstat = map_status(self.pe, fall)[0]
                    fall_decodes = self.decodes_to_real_code(fall)
                    if fstat == "RAW_BACKED_EXECUTABLE" and fall_decodes:
                        queue.append(fall)
                        kind = "NATIVE_FALLTHROUGH"
                        conf = "CANDIDATE"
                    elif fstat == "RAW_BACKED_EXECUTABLE":
                        kind = "RAW_BACKED_NON_CODE"
                        conf = "CONFIRMED"
                    else:
                        kind = fstat
                        conf = "UNKNOWN"
                    self.add_edge(block.rva, insn.rva, "CALL_RETURN_TARGET", fall,
                                  kind, conf, "instruction after call")
                    continue
                if is_jump:
                    self.handle_jump(block, insn, queue)
                    break
                if is_ret:
                    block.terminator = "RET"
                    self.add_edge(block.rva, insn.rva, "RET", None, "RETURN", "CONFIRMED",
                                  f"{insn.mnemonic} {insn.op_str}")
                    break
            if not block.terminator and block.insns:
                block.terminator = "BUDGET"

    def handle_transfer(self, block: Block, insn: Insn, etype: str, queue: list[int]) -> None:
        operand = insn.op_str
        if insn.operands and insn.operands[0].type == X86_OP_IMM:
            dst = insn.operands[0].imm - self.pe.image_base
            status = map_status(self.pe, dst)[0]
            if status == "TVM0_BOUNDARY":
                confidence = "CONFIRMED"
                kind = "TVM0_BOUNDARY"
            elif status == "RAW_BACKED_EXECUTABLE":
                confidence = "CANDIDATE"
                kind = "NATIVE_CANDIDATE"
                queue.append(dst)
            elif status == "VIRTUAL_ONLY":
                confidence = "UNKNOWN"
                kind = "VIRTUAL_ONLY"
            else:
                confidence = "UNKNOWN"
                kind = status
            self.add_edge(block.rva, insn.rva, etype, dst, kind, confidence,
                          f"{insn.mnemonic} {operand}")
        elif insn.operands and insn.operands[0].type == X86_OP_MEM:
            mem = insn.operands[0].mem
            if mem.base == 0 and mem.index == 0:
                slot = mem.disp & 0xFFFFFFFF
                slot_rva = slot - self.pe.image_base
                self.record_indirect(block, insn, slot_rva, "ABSOLUTE_MEMORY_SLOT")
                self.add_edge(block.rva, insn.rva, etype, slot_rva,
                              "INDIRECT_SLOT", "CONFIRMED",
                              f"{insn.mnemonic} {operand}; slot VA {fmt_rva(slot)}")
            else:
                self.record_indirect(block, insn, None, "REGISTER_MEMORY")
                self.add_edge(block.rva, insn.rva, etype, None, "UNRESOLVED_INDIRECT",
                              "UNKNOWN", f"{insn.mnemonic} {operand}")
        else:
            self.record_indirect(block, insn, None, "REGISTER")
            self.add_edge(block.rva, insn.rva, etype, None, "UNRESOLVED_INDIRECT",
                          "UNKNOWN", f"{insn.mnemonic} {operand}")

    def handle_jump(self, block: Block, insn: Insn, queue: list[int]) -> None:
        mnemonic = insn.mnemonic
        if mnemonic == "jmp":
            if insn.operands and insn.operands[0].type == X86_OP_IMM:
                dst = insn.operands[0].imm - self.pe.image_base
                status = map_status(self.pe, dst)[0]
                if status == "TVM0_BOUNDARY":
                    kind, confidence = "TVM0_BOUNDARY", "CONFIRMED"
                elif status == "RAW_BACKED_EXECUTABLE":
                    kind, confidence = "NATIVE_CANDIDATE", "CANDIDATE"
                    queue.append(dst)
                else:
                    kind, confidence = status, "UNKNOWN"
                block.terminator = "JMP"
                self.add_edge(block.rva, insn.rva, "JMP", dst, kind, confidence,
                              f"jmp {insn.op_str}")
            else:
                block.terminator = "JMP_INDIRECT"
                self.record_indirect(block, insn, None, "JUMP_TABLE_OR_REGISTER")
                self.add_edge(block.rva, insn.rva, "JMP", None, "UNRESOLVED_INDIRECT",
                              "UNKNOWN", f"jmp {insn.op_str}")
            return
        # conditional jump: taken + fallthrough
        if insn.operands and insn.operands[0].type == X86_OP_IMM:
            dst = insn.operands[0].imm - self.pe.image_base
            status = map_status(self.pe, dst)[0]
            if status == "RAW_BACKED_EXECUTABLE":
                kind, confidence = "NATIVE_CANDIDATE", "CANDIDATE"
                queue.append(dst)
            elif status == "TVM0_BOUNDARY":
                kind, confidence = "TVM0_BOUNDARY", "CONFIRMED"
            else:
                kind, confidence = status, "UNKNOWN"
            self.add_edge(block.rva, insn.rva, "COND_TAKEN", dst, kind, confidence,
                          f"{insn.mnemonic} {insn.op_str}")
        block.terminator = "COND_JMP"
        fall = insn.end
        fstat = map_status(self.pe, fall)[0]
        if fstat == "RAW_BACKED_EXECUTABLE":
            queue.append(fall)
        self.add_edge(block.rva, insn.rva, "COND_FALLTHROUGH", fall, fstat, "CANDIDATE",
                      "fallthrough")

    def record_indirect(self, block: Block, insn: Insn, slot_rva: int | None,
                        kind: str) -> None:
        slot_value = None
        slot_status = ""
        slot_section = ""
        if slot_rva is not None:
            slot_value_bytes, section, off, st = self.pe.read_rva(slot_rva, 4)
            slot_status = st
            slot_section = section.name if section else ""
            if st == "OK" and len(slot_value_bytes) == 4:
                slot_value = struct.unpack("<I", slot_value_bytes)[0]
        self.indirect_sites.append({
            "site_rva": fmt_rva(insn.rva),
            "block_rva": fmt_rva(block.rva),
            "instruction": f"{insn.mnemonic} {insn.op_str}",
            "kind": kind,
            "slot_rva": fmt_rva(slot_rva) if slot_rva is not None else "",
            "slot_read_status": slot_status,
            "slot_section": slot_section,
            "slot_value": fmt_rva(slot_value) if slot_value is not None else "",
        })

    def decodes_to_real_code(self, rva: int) -> bool:
        """A target is 'real code' only if the first instruction is not zero
        padding and the byte stream is not a run of 0x00. This prevents a
        zero-filled raw region from being treated as executable continuation."""
        data, section, off, status = self.pe.read_rva(rva, 32)
        if status != "OK" or section is None or not section.executable:
            return False
        if len(data) < 2:
            return False
        if data[0] == 0x00 and data[1] == 0x00:
            return False
        # reject long zero runs
        if all(b == 0 for b in data[:16]):
            return False
        insns = list(self.md.disasm(data, self.pe.image_base + rva, count=1))
        return bool(insns)


def main() -> int:
    print("=" * 78)
    print("EXE-CORE-006  Entry-connected Native Bootstrap Recovery")
    print("=" * 78)

    if not SAMPLE.exists():
        print(f"FAIL: sample not found at {SAMPLE}")
        return 1
    actual = sha256_of(SAMPLE)
    print(f"sample        : {SAMPLE}")
    print(f"sha256        : {actual}")
    print(f"expected      : {EXPECTED_SHA256}")
    print(f"sample_match  : {'CONFIRMED' if actual == EXPECTED_SHA256 else 'MISMATCH'}")
    if actual != EXPECTED_SHA256:
        return 1

    pe = ManualPE(SAMPLE)
    print(f"image_base    : 0x{pe.image_base:08X}")
    print(f"entry_rva     : 0x{pe.entry_rva:08X} (expected 0x{EXPECTED_ENTRY_RVA:08X})")
    print(f"entry_match   : {'CONFIRMED' if pe.entry_rva == EXPECTED_ENTRY_RVA else 'MISMATCH'}")
    print()

    # --- Entry structural analysis ---
    entry = analyze_entry(pe)
    print("--- Entry ---")
    for k, v in entry.items():
        print(f"  {k:38s}: {v if not isinstance(v, int) else hex(v)}")
    print()

    # --- Imports ---
    imports = parse_imports(pe)
    print("--- Imports ---")
    for row in imports:
        print(f"  {row['dll']} idx{row['thunk_index']} kind={row['import_kind']} "
              f"ord={row['ordinal']} IAT={row['iat_slot_rva']} value={row['thunk_value']}")
    print()

    # --- Exports ---
    exports = parse_exports(pe)
    print(f"--- Exports ({len(exports)}) ---")
    for row in exports[:30]:
        print(f"  ord{row['ordinal']:3d} rva={row['function_rva']:>12s} "
              f"[{row['mapping_status']}] {row['name'][:60]}")
    print()

    # --- TLS ---
    tls = analyze_tls(pe)
    print("--- TLS ---")
    for k, v in tls.items():
        print(f"  {k:20s}: {v}")
    print()

    # --- Entry-connected CFG ---
    cfg = EntryConnectedCFG(pe)
    cfg.analyze()
    print("--- Entry-connected CFG ---")
    print(f"  blocks          : {len(cfg.blocks)}")
    print(f"  edges           : {len(cfg.edges)}")
    print(f"  indirect sites  : {len(cfg.indirect_sites)}")
    print(f"  decode failures : {len(cfg.decode_failures)}")
    for row in cfg.edges:
        print(f"  {row['source_block']} @{row['instruction_rva']} {row['edge_type']:16s} "
              f"-> {row['target_rva']:>12s} [{row['target_kind']}] {row['confidence']}")
    print()

    # --- artifacts ---
    write_csv(ROOT / "exe_core006_entry_edges.csv",
              ["source_block", "instruction_rva", "edge_type", "target_rva",
               "target_kind", "confidence", "evidence"], cfg.edges)
    write_csv(ROOT / "exe_core006_indirect_slots.csv",
              ["site_rva", "block_rva", "instruction", "kind", "slot_rva",
               "slot_read_status", "slot_section", "slot_value"], cfg.indirect_sites)
    write_csv(ROOT / "exe_core006_imports.csv",
              ["descriptor_index", "dll", "dll_name_rva", "oft_rva", "first_thunk_rva",
               "iat_slot_rva", "int_slot_rva", "thunk_index", "thunk_value",
               "import_kind", "ordinal", "hint_name_rva"], imports)
    write_csv(ROOT / "exe_core006_exports.csv",
              ["dll", "ordinal", "index", "function_rva", "name_rva", "name",
               "mapping_status"], exports)

    print("artifacts written: exe_core006_entry_edges.csv, "
          "exe_core006_indirect_slots.csv, exe_core006_imports.csv, "
          "exe_core006_exports.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


if __name__ == "__main__":
    raise SystemExit(main())
