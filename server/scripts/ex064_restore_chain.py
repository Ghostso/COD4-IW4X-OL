# EX-064 TASK H/K: recover the IIPSLaunchRestore.dll internal chain and its
# external entry (exports / who loads it).
import json

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex064_restore_gpa import Img

RESTORE = r"工具\EX035_DIR\IIPS\IIPSLaunchRestore.dll"


def main():
    img = Img(RESTORE)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True

    print("=" * 78)
    print("IIPSLaunchRestore.dll exports")
    print("=" * 78)
    pe = img.pe
    if hasattr(pe, "DIRECTORY_ENTRY_EXPORT"):
        for e in pe.DIRECTORY_ENTRY_EXPORT.symbols:
            nm = e.name.decode() if e.name else "ord%d" % e.ordinal
            print("   %-32s RVA 0x%X" % (nm, e.address))
    else:
        print("   (no exports)")

    print()
    print("=" * 78)
    print("function that owns the GetResourceManagerII site at 0x3C89")
    print("=" * 78)
    pe = img.pe
    # find function boundaries via the export table and known prologues
    for target in (0x3B0D, 0x3C89):
        # walk back to the nearest SEH/standard prologue
        r = target
        while r > 0x1000:
            b = img.read(r, 8)
            if (b[:3] == b"\x55\x8b\xec") or \
                    (b[0] == 0x6A and b[1] == 0xFF and b[2] == 0x68):
                # verify it is a real prologue by checking the byte before
                prev = img.read(r - 1, 1)
                if prev in (b"\xc3", b"\xcc", b"\x90") or r == 0x1000:
                    break
            r -= 1
        print("   target 0x%X  nearest prologue 0x%X" % (target, r))

    print()
    print("=" * 78)
    print("who calls sub_3B0D (the function containing the LoadLibrary site)?")
    print("=" * 78)
    lo, hi = img.codesec()
    hits = []
    rva = lo
    while rva < hi:
        insn = next(md.disasm(img.read(rva, 16), img.base + rva), None)
        if insn is None:
            rva += 1
            continue
        if insn.mnemonic == "call" and insn.operands:
            op = insn.operands[0]
            if op.type == X86_OP_IMM:
                t = op.imm - img.base
                if t in (0x3B0D, 0x3B00, 0x3600, 0x79B0):
                    hits.append((rva, t))
        rva += insn.size
    for r, t in sorted(set(hits)):
        print("   0x%05X call sub_%X" % (r, t))

    print()
    print("=" * 78)
    print("string refs identifying the caller of the restore thread")
    print("=" * 78)
    for nm, va in (("IIPSLaunchRestoreProc", 0x10073AC4),
                   ("[CallBackThread::Init()]...", 0x100733D0),
                   ("IIPSRestoreManager", 0x100747F8)):
        needle = va.to_bytes(4, "little")
        st = 0
        out = []
        while True:
            i = img.data.find(needle, st)
            if i < 0:
                break
            out.append(i)
            st = i + 1
        rvas = []
        for o in out:
            for (snm, sva, vs, raw, rs, ch) in img.secs:
                if raw <= o < raw + rs:
                    rvas.append("0x%X" % (sva + (o - raw)))
                    break
        print("   %-32s -> %s" % (nm, rvas or "NONE"))


if __name__ == "__main__":
    main()
