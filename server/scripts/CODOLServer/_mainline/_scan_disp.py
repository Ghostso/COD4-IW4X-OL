"""Scan the decrypted image for every instruction that references a given
disp32, printing VA + the raw instruction bytes + a disassembly window."""
import os
import struct
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
IMAGE = os.path.join(HERE, "_dyn100_run_20260925_182324", "live", "image_best.bin")
BASE = 0x400000


def main(argv):
    disp = int(argv[0], 16)
    back = int(argv[1], 16) if len(argv) > 1 else 0x10
    fwd = int(argv[2], 16) if len(argv) > 2 else 0x20
    data = open(IMAGE, "rb").read()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    needle = struct.pack("<I", disp)
    hits = []
    start = 0
    while True:
        i = data.find(needle, start)
        if i < 0:
            break
        hits.append(i)
        start = i + 1
    print("disp 0x%X : %d raw occurrences" % (disp, len(hits)))
    for i in hits:
        # walk back to a plausible instruction start and disassemble forward
        s = max(0, i - back)
        blob = data[s:i + 4 + fwd]
        printed = False
        for ins in md.disasm(blob, BASE + s):
            lo = ins.address - BASE
            hi = lo + len(ins.bytes)
            if lo <= i < hi:            # this instruction contains the disp
                print("  %08X  %-24s %s %s" % (ins.address, ins.bytes.hex(),
                                               ins.mnemonic, ins.op_str))
                printed = True
                break
        if not printed:
            print("  %08X  (?) %s" % (BASE + i,
                                      data[i - 6:i + 10].hex()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
