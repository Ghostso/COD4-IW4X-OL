#!/usr/bin/env python3
"""s138_xref_text: linear-disassemble .text and report every instruction whose
operand references a given absolute VA. Classifies read/write/RMW/push/lea.
usage: python -I tools\\s138_xref_text.py 0x76446B0 [0x...]
"""
import struct
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)


def text_range():
    # PE section table: find .text
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    nsec = struct.unpack_from("<H", d, pe + 6)[0]
    optsz = struct.unpack_from("<H", d, pe + 20)[0]
    base = pe + 24 + optsz
    secs = []
    for i in range(nsec):
        o = base + i * 40
        name = d[o:o + 8].rstrip(b"\x00").decode("latin1")
        vsize = struct.unpack_from("<I", d, o + 8)[0]
        vaddr = struct.unpack_from("<I", d, o + 12)[0]
        rawsz = struct.unpack_from("<I", d, o + 16)[0]
        rawptr = struct.unpack_from("<I", d, o + 20)[0]
        secs.append((name, vaddr, vsize, rawptr, rawsz))
    return secs


def classify(mn, ops, tgtstr):
    if mn == "lea":
        return "LEA"
    if mn == "push":
        return "PUSH"
    if mn in ("cmp", "test"):
        return "READ"
    if mn == "mov" and ops.startswith("dword ptr [" + tgtstr):
        return "READ"
    if mn == "mov" and ops.rstrip().endswith(tgtstr):
        return "WRITE"
    if mn in ("inc", "dec", "add", "sub", "or", "and", "xor"):
        return "RMW"
    if mn in ("movzx", "movsx", "mov"):
        return "R?"
    return mn


def run(tgt):
    ts = "0x%x" % tgt
    secs = text_range()
    # first section is the code section (this image names it .tp3, vaddr==rawptr==0x1000)
    name, vaddr, vsize, rawptr, rawsz = secs[0]
    print("== refs to 0x%08X in code section '%s' (vaddr 0x%X size 0x%X) ==" % (
        tgt, name, vaddr, vsize))
    code = d[rawptr:rawptr + rawsz]
    base = VA + vaddr
    refs = []
    for ins in md.disasm(code, base):
        if ts in ins.op_str.lower():
            refs.append(ins)
    print("  %d instruction refs" % len(refs))
    for ins in refs:
        print("  0x%08X  %-24s %-7s %s %s" % (
            ins.address, ins.bytes.hex(),
            classify(ins.mnemonic, ins.op_str, ts), ins.mnemonic, ins.op_str))
    return refs


if __name__ == "__main__":
    for a in sys.argv[1:]:
        run(int(a, 0))
        print()
