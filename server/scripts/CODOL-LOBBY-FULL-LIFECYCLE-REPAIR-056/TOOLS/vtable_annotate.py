"""Annotate a vftable: list slots and disassemble each briefly.

Usage:
  python -I vtable_annotate.py <image.bin> <vftable_hex> [n_slots]
"""
import capstone
import struct
import sys

BASE = 0x400000
IMG_LO, IMG_HI = 0x00401000, 0x00EA59000


def main():
    img = sys.argv[1]
    vft = int(sys.argv[2], 16)
    n_max = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    data = open(img, "rb").read()
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = True

    print("vftable 0x%08X" % vft)
    for i in range(n_max):
        off = vft - BASE + i * 4
        if off + 4 > len(data):
            break
        fn = struct.unpack_from("<I", data, off)[0]
        if not (IMG_LO <= fn <= IMG_HI):
            print("  [%2d] 0x%08X  <not a code pointer -> end>" % (i, fn))
            break
        print("  [%2d] 0x%08X" % (i, fn))
        foff = fn - BASE
        code = data[foff:foff + 160]
        n = 0
        for ins in md.disasm(code, fn):
            note = ""
            if ins.id in (capstone.x86.X86_INS_CALL, capstone.x86.X86_INS_JMP):
                for op in ins.operands:
                    if op.type == capstone.x86.X86_OP_IMM:
                        note += "   ; -> 0x%08X" % op.imm
            print("       0x%08X  %-22s %s %s%s" % (ins.address, ins.bytes.hex(),
                                                    ins.mnemonic, ins.op_str, note))
            n += 1
            if n >= 10:
                break
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
