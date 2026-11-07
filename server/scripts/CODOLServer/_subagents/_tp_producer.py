#!/usr/bin/env python3
"""Read-only disassembler for tcls_core.exe (the TCLS SHM producer).

Pure static analysis of the on-disk PE.  ASCII-only output.
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

import capstone
import pefile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
DEFAULT_EXE = ROOT / "WeGame" / "tcls" / "tcls_core.exe"


def load(path: Path):
    data = path.read_bytes()
    pe = pefile.PE(str(path), fast_load=False)
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = True
    return pe, data, md


def raw_for_va(pe, va):
    base = pe.OPTIONAL_HEADER.ImageBase
    rva = va - base
    for sec in pe.sections:
        lo = sec.VirtualAddress
        size = max(sec.Misc_VirtualSize, sec.SizeOfRawData)
        if lo <= rva < lo + size and (rva - lo) < sec.SizeOfRawData:
            return sec.PointerToRawData + (rva - lo)
    return None


def read_va(pe, data, va, size):
    off = raw_for_va(pe, va)
    if off is None or off + size > len(data):
        return None
    return data[off:off + size]


def imports_by_va(pe):
    out = {}
    if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
        for desc in pe.DIRECTORY_ENTRY_IMPORT:
            dll = desc.dll.decode("latin1", "replace")
            for imp in desc.imports:
                name = (imp.name.decode("latin1", "replace")
                        if imp.name else "ord%d" % imp.ordinal)
                out[imp.address] = "%s!%s" % (dll, name)
    return out


def notes_for(pe, data, imp, insn):
    notes = []
    if insn.mnemonic in ("call", "jmp") and insn.operands:
        op = insn.operands[0]
        if op.type == capstone.x86.X86_OP_MEM and op.mem.base == 0 and op.mem.index == 0:
            notes.append(imp.get(op.mem.disp, "IAT@0x%X" % op.mem.disp))
    if insn.mnemonic in ("push", "mov") and insn.operands:
        op = insn.operands[-1]
        if op.type == capstone.x86.X86_OP_IMM:
            raw = read_va(pe, data, op.imm, 128)
            if raw:
                out = []
                for i in range(0, len(raw) - 1, 2):
                    ch = raw[i] | (raw[i + 1] << 8)
                    if ch == 0:
                        break
                    out.append(chr(ch) if 32 <= ch < 127 else "?")
                joined = "".join(out)
                if len(joined) > 3 and joined.isprintable():
                    notes.append('L"%s"' % joined)
    return notes


def dump(pe, data, md, imp, start, end):
    off = raw_for_va(pe, start)
    if off is None:
        raise SystemExit("no raw bytes for 0x%X" % start)
    blob = data[off:off + (end - start)]
    lines = []
    pos = 0
    while pos < len(blob):
        insn = next(md.disasm(blob[pos:], start + pos), None)
        if insn is None:
            pos += 1
            continue
        n = notes_for(pe, data, imp, insn)
        lines.append("0x%08X  %-24s %-8s %-34s%s" % (
            insn.address, insn.bytes.hex(), insn.mnemonic, insn.op_str,
            ("  ; " + " | ".join(n)) if n else ""))
        pos += insn.size
    return lines


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("start")
    ap.add_argument("end")
    ap.add_argument("--out")
    ap.add_argument("--exe", default=str(DEFAULT_EXE))
    args = ap.parse_args()
    pe, data, md = load(Path(args.exe))
    imp = imports_by_va(pe)
    lines = dump(pe, data, md, imp, int(args.start, 16), int(args.end, 16))
    text = "\n".join(lines) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="ascii")
        print("WROTE %s lines=%d" % (args.out, len(lines)))
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
