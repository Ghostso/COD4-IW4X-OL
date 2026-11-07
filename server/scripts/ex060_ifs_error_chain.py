# EX-060 TASK 4/5: build the IIPS failure-state production chain by
# recovering the functions that reference the IFS error strings.
import json
import re
import struct
from collections import OrderedDict

from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_IMM, X86_OP_MEM

from ex060_iips_cfg import Image, DLL, build_imports
from ex060_cfg_engine import Function, callsite_info


def rva_for_raw(img, off):
    for s in img.sections:
        if s["raw"] <= off < s["raw"] + s["rawsize"]:
            return s["va"] + (off - s["raw"])
    return None


def find_push_refs(img, va):
    """Locate 'push imm32' instructions whose immediate == va, within .text."""
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    out = []
    lo, hi = 0x1000, 0x33000
    rva = lo
    while rva < hi:
        code = img.read(rva, 16)
        insn = next(md.disasm(code, img.base + rva), None)
        if insn is None:
            rva += 1
            continue
        if insn.mnemonic in ("push", "mov", "lea", "cmp") and insn.operands:
            op = insn.operands[0]
            if op.type == X86_OP_IMM and op.imm == va:
                out.append((rva, insn.mnemonic, insn.op_str))
        rva += insn.size
    return out


def main():
    img = Image(DLL)
    imports = build_imports(img)
    raw = open(DLL, "rb").read()

    targets = [
        "IIPSERR_IFS_LOAD_DLL_ERROR",
        "IIPSERR_IFS_DLL_CANT_FIND_FUNCTION",
        "IIPSERR_IFS_INIT",
        "IIPSERR_IFS_OPEN_FAIL",
        "IIPSERR_SHARESTATE_INIT",
        "IIPSERR_IIPSHOST_INIT",
        "IIPSERR_WINMSG_INIT",
    ]
    print("=" * 78)
    print("IFS/Host error string -> RVA -> push-ref sites (producers)")
    print("=" * 78)
    for t in targets:
        i = raw.find(t.encode())
        if i < 0:
            print("%-36s NOT FOUND" % t)
            continue
        rva = rva_for_raw(img, i)
        va = img.base + rva
        refs = find_push_refs(img, va)
        print("%-36s str RVA 0x%05X VA 0x%08X  push-refs=%d" % (
            t, rva, va, len(refs)))
        for r, m, o in refs:
            print("      +0x%X  %s %s" % (r, m, o))


if __name__ == "__main__":
    main()
