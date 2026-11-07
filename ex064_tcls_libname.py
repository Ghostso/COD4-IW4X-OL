# EX-064 TASK K: confirm which DLL tcls_core.exe loads before calling
# GetProcAddress("CreateIIPSRepair").
import json

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex064_tcls_gpa import Img

TCLS = r"WeGame\tcls\tcls_core.exe"


def main():
    img = Img(TCLS)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True

    print("=" * 78)
    print("IIPSLaunchRestore / IIPS related strings in tcls_core.exe")
    print("=" * 78)
    import re
    for m in re.finditer(rb"[ -~]{4,}", img.data):
        s = m.group()
        if b"iips" in s.lower() or b"IIPS" in s:
            rva, sec = img.raw2rva(m.start())
            print("   VA 0x%08X sec %-8s %r" % (
                img.base + rva if rva else 0, sec, s[:100]))

    print()
    print("=" * 78)
    print("the dll-name construction before LoadLibraryW at 0x8D353")
    print("=" * 78)
    lo, _ = img.codesec()
    r = 0x8D280
    while r <= 0x8D360:
        insn = next(md.disasm(img.read(r, 16), img.base + r), None)
        if insn is None:
            r += 1
            continue
        mark = ""
        if insn.mnemonic == "call" and insn.operands:
            op = insn.operands[0]
            if op.type == X86_OP_MEM and op.mem.base == 0:
                n = img.imports.get(op.mem.disp - img.base)
                if n:
                    mark = "   ; %s!%s" % n
            elif op.type == X86_OP_IMM:
                mark = "   ; -> sub_%X" % (op.imm - img.base)
        if insn.operands and insn.operands[0].type == X86_OP_IMM:
            t = insn.operands[0].imm - img.base
            if 0 <= t < img.size:
                s = img.read(t, 100).split(b"\x00")[0]
                if len(s) >= 4 and all(32 <= c < 127 for c in s):
                    mark += '   ; "%s"' % s.decode()
                elif len(s) >= 4:
                    try:
                        w = img.read(t, 100)
                        ws = w.decode("utf-16-le").split("\x00")[0]
                        if len(ws) >= 4 and all(32 <= ord(c) < 0x3000
                                                for c in ws):
                            mark += '   ; L"%s"' % ws
                    except Exception:
                        pass
        print("   0x%05X  %-24s %s %s%s" % (
            r, insn.bytes.hex(), insn.mnemonic, insn.op_str, mark))
        r += insn.size


if __name__ == "__main__":
    main()
