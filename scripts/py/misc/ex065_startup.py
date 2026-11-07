# EX-065 PHASE 1: disassemble tcls_core.exe entry point, TLS callbacks, and
# walk the startup chain to sub_8D2A2.
import json

import capstone as cs
import pefile
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

TCLS = r"WeGame\tcls\tcls_core.exe"

from ex065_tcls_img import Img


def dump(img, md, entry, limit=90, title=None):
    print("=" * 78)
    print(title or ("disassembly from 0x%X" % entry))
    print("=" * 78)
    rva = entry
    n = 0
    while n < limit:
        insn = next(md.disasm(img.read(rva, 16), img.base + rva), None)
        if insn is None:
            print("   (decode stop at 0x%X)" % rva)
            break
        mark = ""
        if insn.mnemonic == "call" and insn.operands:
            op = insn.operands[0]
            if op.type == X86_OP_MEM and op.mem.base == 0:
                nm = img.imports.get(op.mem.disp - img.base)
                mark = "   ; %s!%s" % nm if nm else "   ; IAT 0x%X" % op.mem.disp
            elif op.type == X86_OP_IMM:
                mark = "   ; -> sub_%X" % (op.imm - img.base)
            elif op.type == X86_OP_REG:
                mark = "   ; IND %s" % md.reg_name(op.reg)
            elif op.type == X86_OP_MEM:
                mark = "   ; IND [%s+0x%X]" % (
                    md.reg_name(op.mem.base) if op.mem.base else "-",
                    op.mem.disp)
        if insn.mnemonic in ("push", "mov", "lea") and insn.operands:
            op = insn.operands[-1]
            if op.type == X86_OP_IMM:
                t = op.imm - img.base
                if 0 <= t < img.size:
                    s = img.read(t, 90).split(b"\x00")[0]
                    if len(s) >= 4 and all(32 <= c < 127 for c in s):
                        mark += '   ; "%s"' % s.decode()
        print("   0x%05X  %-24s %s %s%s" % (
            rva, insn.bytes.hex(), insn.mnemonic, insn.op_str, mark))
        if insn.mnemonic.startswith("ret") or insn.mnemonic == "int3":
            break
        if insn.mnemonic == "jmp" and "0x" in insn.op_str:
            break
        rva += insn.size
        n += 1


def main():
    img = Img(TCLS)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True

    ep = img.pe.OPTIONAL_HEADER.AddressOfEntryPoint
    dump(img, md, ep, 80, "PE ENTRY POINT RVA 0x%X" % ep)

    # TLS callbacks
    print()
    tls_rva = img.pe.OPTIONAL_HEADER.DATA_DIRECTORY[
        pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_TLS"]].VirtualAddress
    if tls_rva:
        print("=" * 78)
        print("TLS directory at RVA 0x%X" % tls_rva)
        print("=" * 78)
        raw = img.read(tls_rva, 24)
        print("  raw: %s" % raw.hex())
        start, end, idx, cbs, z1, chars = (
            int.from_bytes(raw[0:4], "little"),
            int.from_bytes(raw[4:8], "little"),
            int.from_bytes(raw[8:12], "little"),
            int.from_bytes(raw[12:16], "little"),
            int.from_bytes(raw[16:20], "little"),
            int.from_bytes(raw[20:24], "little"))
        print("  StartAddressOfRawData   VA 0x%X" % start)
        print("  EndAddressOfRawData     VA 0x%X" % end)
        print("  AddressOfIndex          VA 0x%X" % idx)
        print("  AddressOfCallBacks      VA 0x%X" % cbs)
        if cbs:
            r = cbs - img.base
            for i in range(8):
                v = int.from_bytes(img.read(r + i * 4, 4), "little")
                if v == 0:
                    break
                print("  callback[%d] RVA 0x%X" % (i, v - img.base))
                dump(img, md, v - img.base, 30,
                     "TLS CALLBACK %d @ RVA 0x%X" % (i, v - img.base))

    print()
    print("=" * 78)
    print("CRT startup: does the entry point call the CRT init?")
    print("=" * 78)


if __name__ == "__main__":
    main()
