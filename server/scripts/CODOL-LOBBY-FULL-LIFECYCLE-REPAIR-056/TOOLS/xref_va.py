"""Find code that references a VA (string/global), then disassemble around each hit.

Usage:
  python -I xref_va.py <image.bin> <va_hex> [window] [--insn N]
"""
import capstone
import struct
import sys

BASE = 0x400000
IMG_LO, IMG_HI = 0x00401000, 0x00EA59000


def main():
    img = sys.argv[1]
    va = int(sys.argv[2], 16)
    window = int(sys.argv[3]) if len(sys.argv) > 3 and not sys.argv[3].startswith("--") else 160
    ninsn = 12
    if "--insn" in sys.argv:
        ninsn = int(sys.argv[sys.argv.index("--insn") + 1])

    data = open(img, "rb").read()
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = True

    needle = struct.pack("<I", va)
    hits = []
    start = 0
    while True:
        i = data.find(needle, start)
        if i < 0:
            break
        hits.append(BASE + i)
        start = i + 1

    print("references to 0x%08X : %d" % (va, len(hits)))
    for h in hits:
        kind = "code?" if (IMG_LO <= h <= 0x00E5D3000) else "data/vtable"
        print("\n--- ref at 0x%08X (%s) ---" % (h, kind))
        # find the enclosing instruction stream: start a bit earlier and align
        lo = max(BASE, h - window)
        code = data[lo - BASE: h - BASE + 16]
        insns = list(md.disasm(code, lo))
        # keep only instructions that end at or after h
        sel = [ins for ins in insns if ins.address + ins.size > h][:ninsn]
        for ins in sel:
            note = ""
            if ins.id in (capstone.x86.X86_INS_CALL, capstone.x86.X86_INS_JMP):
                for op in ins.operands:
                    if op.type == capstone.x86.X86_OP_IMM:
                        note = "  ; -> 0x%08X" % op.imm
            print("    0x%08X  %-18s %s %s%s" % (ins.address, ins.bytes.hex(),
                                                 ins.mnemonic, ins.op_str, note))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
