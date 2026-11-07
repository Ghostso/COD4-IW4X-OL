#!/usr/bin/env python3
"""Read-only disassembler helper for TenProxy.dll (image base 0x10000000).

Pure static analysis of the on-disk PE.  ASCII-only output.  No process is
launched, no mapping is created, no target file is modified.
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
DEFAULT_DLL = ROOT / "COD OL" / "TenProxy.dll"
IMAGE_BASE = 0x10000000


def load(path: Path):
    data = path.read_bytes()
    pe = pefile.PE(str(path), fast_load=False)
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = True
    return pe, data, md


def raw_for_rva(pe, rva):
    for sec in pe.sections:
        lo = sec.VirtualAddress
        size = max(sec.Misc_VirtualSize, sec.SizeOfRawData)
        if lo <= rva < lo + size:
            delta = rva - lo
            if delta < sec.SizeOfRawData:
                return sec.PointerToRawData + delta
    return None


def read_va(pe, data, va, size):
    off = raw_for_rva(pe, va - pe.OPTIONAL_HEADER.ImageBase)
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


def rel_target(va, size, ptr):
    """Resolve a rel32 jump/call at va pointing to ptr."""
    if not (va <= ptr < va + size):
        return None
    rel = struct.unpack_from("<i", ptr.to_bytes(4, "little"), 0)[0]
    return None


def annotate(pe, data, imp, insn):
    notes = []
    if insn.mnemonic in ("call", "jmp") and insn.operands:
        op = insn.operands[0]
        if op.type == capstone.x86.X86_OP_MEM and op.mem.base == 0 and op.mem.index == 0:
            notes.append(imp.get(op.mem.disp, "IAT@0x%X" % op.mem.disp))
    if insn.mnemonic in ("push", "mov") and insn.operands:
        op = insn.operands[-1]
        if op.type == capstone.x86.X86_OP_IMM and 0x10000000 <= op.imm < 0x10040000:
            raw = read_va(pe, data, op.imm, 96)
            if raw:
                text = []
                for i in range(0, len(raw) - 1, 2):
                    ch = raw[i] | (raw[i + 1] << 8)
                    if ch == 0:
                        break
                    text.append(chr(ch) if 32 <= ch < 127 else "?")
                joined = "".join(text)
                if len(joined) > 3 and joined.isprintable():
                    notes.append('L"%s"' % joined)
    return notes


def cmd_dis(args):
    pe, data, md = load(Path(args.dll))
    imp = imports_by_va(pe)
    start = int(args.start, 16)
    end = int(args.end, 16)
    off = raw_for_rva(pe, start - IMAGE_BASE)
    if off is None:
        raise SystemExit("no raw bytes for 0x%X" % start)
    blob = data[off:off + (end - start)]
    pos = 0
    while pos < len(blob):
        insn = next(md.disasm(blob[pos:], start + pos), None)
        if insn is None:
            print("0x%08X  %-20s db 0x%02X" % (start + pos, "", blob[pos]))
            pos += 1
            continue
        notes = annotate(pe, data, imp, insn)
        print("0x%08X  %-24s %-8s %-34s%s" % (
            insn.address, insn.bytes.hex(), insn.mnemonic, insn.op_str,
            ("  ; " + " | ".join(notes)) if notes else ""))
        pos += insn.size


def cmd_slice(args):
    pe, data, _ = load(Path(args.dll))
    vas = [int(a, 16) for a in args.va]
    for va in vas:
        raw = read_va(pe, data, va, args.size)
        print("0x%08X %s" % (va, raw.hex() if raw else "<no raw>"))
        if args.dwords:
            for i in range(0, len(raw), 4):
                val = struct.unpack_from("<I", raw, i)[0]
                print("    +0x%03X = 0x%08X" % (i, val))


def cmd_vtable(args):
    pe, data, _ = load(Path(args.dll))
    base = int(args.base, 16)
    raw = read_va(pe, data, base, 4 * args.count)
    for i in range(args.count):
        ptr = struct.unpack_from("<I", raw, i * 4)[0]
        stub = read_va(pe, data, ptr, 5)
        target = ptr
        if stub and stub[0] == 0xE9:
            rel = struct.unpack_from("<i", stub, 1)[0]
            target = (ptr + 5 + rel) & 0xFFFFFFFF
        print("+0x%02X  0x%08X  ->  0x%08X" % (i * 4, base + i * 4, target))


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("dis", cmd_dis), ("vtable", cmd_vtable)):
        p = sub.add_parser(name)
        p.add_argument("--dll", default=str(DEFAULT_DLL))
        p.set_defaults(func=fn)
        if name == "dis":
            p.add_argument("start")
            p.add_argument("end")
        else:
            p.add_argument("--base", default="0x100205D0")
            p.add_argument("--count", type=int, default=18)
    p = sub.add_parser("slice")
    p.add_argument("--dll", default=str(DEFAULT_DLL))
    p.add_argument("--size", type=int, default=0x40)
    p.add_argument("--dwords", action="store_true")
    p.add_argument("va", nargs="+")
    p.set_defaults(func=cmd_slice)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main() or 0)
