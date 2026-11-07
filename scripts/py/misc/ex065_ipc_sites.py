# EX-065 PHASE 3: recover the named objects used by the IPC sites in
# tcls_core.exe, especially OpenFileMapping / CreateMutex / events.
import json
import re

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex065_tcls_img import Img

TCLS = r"WeGame\tcls\tcls_core.exe"


def main():
    img = Img(TCLS)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True

    sites = [
        (0x4D7F3, "OpenFileMappingA"), (0x8993E, "OpenFileMappingA"),
        (0xC2B8, "OpenFileMappingW"), (0x1E745, "OpenFileMappingW"),
        (0x7A76C, "OpenFileMappingW"),
        (0x4D837, "CreateFileMappingA"), (0x5C487, "CreateFileMappingA"),
        (0xC854, "CreateMutexW"), (0x5C853, "CreateMutexW"),
        (0x62620, "OpenMutexW"), (0x7B032, "OpenEventW"),
    ]
    for site, api in sites:
        print("=" * 78)
        print("%s at 0x%X" % (api, site))
        print("=" * 78)
        lo = site - 0x60
        r = lo
        n = 0
        while r <= site + 0x30 and n < 50:
            insn = next(md.disasm(img.read(r, 16), img.base + r), None)
            if insn is None:
                r += 1
                continue
            mark = ""
            if insn.mnemonic == "call" and insn.operands:
                op = insn.operands[0]
                if op.type == X86_OP_MEM and op.mem.base == 0:
                    nm = img.imports.get(op.mem.disp - img.base)
                    if nm:
                        mark = "   ; %s!%s" % nm
                elif op.type == X86_OP_IMM:
                    mark = "   ; -> sub_%X" % (op.imm - img.base)
            if insn.operands:
                for op in insn.operands:
                    if op.type == X86_OP_IMM:
                        t = op.imm - img.base
                        if 0 <= t < img.size:
                            s = img.read(t, 90).split(b"\x00")[0]
                            if len(s) >= 4 and all(32 <= c < 127 for c in s):
                                mark += '   ; "%s"' % s.decode()
            star = "   <<<" if r == site else ""
            print("   0x%05X  %-22s %s %s%s%s" % (
                r, insn.bytes.hex(), insn.mnemonic, insn.op_str, mark, star))
            r += insn.size
            n += 1
        print()

    print("=" * 78)
    print("all .rdata strings containing 'Shared', 'Global\\\\', 'Local\\\\',")
    print("'mutex', 'Mutex', 'Event', 'Pipe', 'MEMORY', 'MEM'")
    print("=" * 78)
    pats = [b"Shared", b"Global\\", b"Local\\", b"Mutex", b"mutex",
            b"EVENT", b"Event", b"Pipe", b"MEMORY", b"SHARED"]
    seen = set()
    for m in re.finditer(rb"[ -~]{4,}", img.data):
        s = m.group()
        if any(p in s for p in pats):
            rva, sec = img.raw2rva(m.start())
            if rva is None or sec not in (".rdata", ".data"):
                continue
            if s in seen:
                continue
            seen.add(s)
            print("  RVA 0x%07X sec %-8s %r" % (rva, sec, s[:110]))


if __name__ == "__main__":
    main()
