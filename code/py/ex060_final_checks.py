# EX-060 final verification: sub_4310 semantics and the absence of any
# 0x8189FEC producer inside iips.dll.
import json
import re
import struct

import capstone as cs

from ex060_iips_cfg import Image, DLL, build_imports
from ex060_cfg_engine import Function, callsite_info


def main():
    img = Image(DLL)
    imports = build_imports(img)

    print("=" * 74)
    print("sub_4310 semantics (error message store helper)")
    print("=" * 74)
    sub = Function(img, 0x4310, "sub_4310").run().build_bbs()
    print("insns=%d bbs=%d" % (len(sub.insns), len(sub.bbs)))
    for rva, insn in list(sub.insns.items())[:45]:
        mark = ""
        if insn.mnemonic == "call":
            ci = callsite_info(sub, rva, insn, img, imports)
            keep = {k: v for k, v in ci.items()
                    if k in ("kind", "dll", "import", "target_rva", "reg")}
            mark = "   ; " + json.dumps(keep)
        print("   %08X  %-20s %s %s%s" % (
            insn.address, insn.bytes.hex(), insn.mnemonic, insn.op_str, mark))
    print("   returns:")
    for start, b in sub.bbs.items():
        if b.kind == "ret":
            insn = sub.insns[b.insns[-1]]
            print("      0x%X %s %s" % (start, insn.mnemonic, insn.op_str))

    print()
    print("=" * 74)
    print("Does iips.dll contain ANY absolute ref into the EXE image range?")
    print("=" * 74)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True
    hit = 0
    for rva in range(0x1000, 0x33000):
        if not img.is_code(rva):
            continue
        for insn in md.disasm(img.read(rva, 15), img.base + rva):
            for op in insn.operands:
                if (op.type == cs.x86.X86_OP_MEM and op.mem.base == 0
                        and op.mem.index == 0):
                    if 0x400000 <= op.mem.disp < 0xEA59000:
                        print("   +0x%X  %s %s" % (
                            rva, insn.mnemonic, insn.op_str))
                        hit += 1
            break
    if not hit:
        print("   NONE  -> iips.dll never directly addresses an EXE VA.")

    print()
    print("=" * 74)
    print("Literal / string search in iips.dll")
    print("=" * 74)
    raw = open(DLL, "rb").read()
    print("   le32 0x8189FEC count:", raw.count(struct.pack("<I", 0x8189FEC)))
    print("   ascii '8189FEC'    :", raw.count(b"8189FEC"))
    print("   IIPSERR_* strings:")
    for m in re.finditer(rb"IIPSERR_[A-Z_]+", raw):
        print("      %r at raw 0x%X" % (m.group(), m.start()))
    print("   IIPS* strings:")
    seen = set()
    for m in re.finditer(rb"IIPS[A-Za-z_]{2,}", raw):
        if m.group() not in seen:
            seen.add(m.group())
            print("      %r at raw 0x%X" % (m.group(), m.start()))

    print()
    print("=" * 74)
    print("iips.dll imports touching shared state / messaging")
    print("=" * 74)
    for d in img.pe.DIRECTORY_ENTRY_IMPORT:
        for imp in d.imports:
            n = imp.name.decode() if imp.name else "ord%d" % imp.ordinal
            if any(k in n for k in ("MessageBox", "OpenFileMapping",
                                    "CreateMutex", "ShellExecute",
                                    "CreateFileMapping", "MapViewOfFile")):
                print("   %s!%s at IAT 0x%X" % (
                    d.dll.decode(), n, imp.address - img.base))


if __name__ == "__main__":
    main()
