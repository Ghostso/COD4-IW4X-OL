# EX-064 TASK K: recover the LoadLibraryW argument in IIPSLaunchRestore.dll.
import json
import re

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex064_restore_gpa import Img

RESTORE = r"工具\EX035_DIR\IIPS\IIPSLaunchRestore.dll"


def sec_of(img, raw_off):
    for (nm, sva, vs, raw, rs, ch) in img.secs:
        if raw <= raw_off < raw + rs:
            return nm, sva + (raw_off - raw)
    return None, None


def main():
    img = Img(RESTORE)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True

    print("=" * 78)
    print("iips-related strings in IIPSLaunchRestore.dll")
    print("=" * 78)
    for m in re.finditer(rb"[ -~]{4,}", img.data):
        s = m.group()
        if b"iips" in s.lower():
            nm, rva = sec_of(img, m.start())
            print("  VA 0x%08X sec %-8s %r" % (img.base + rva, nm, s))

    print()
    print("=" * 78)
    print("LoadLibraryW region 0x3B00..0x3C50")
    print("=" * 78)
    rva = 0x3B00
    while rva <= 0x3C50:
        insn = next(md.disasm(img.read(rva, 16), img.base + rva), None)
        if insn is None:
            rva += 1
            continue
        mark = ""
        for op in insn.operands:
            if op.type == X86_OP_IMM:
                t = op.imm - img.base
                if 0 <= t < img.size:
                    s = img.read(t, 80)
                    txt = s.split(b"\x00")[0]
                    if len(txt) >= 3 and all(32 <= c < 127 for c in txt):
                        mark = '   ; imm -> "%s"' % txt.decode()
        print("   0x%05X  %-24s %s %s%s" % (
            rva, insn.bytes.hex(), insn.mnemonic, insn.op_str, mark))
        rva += insn.size


if __name__ == "__main__":
    main()
