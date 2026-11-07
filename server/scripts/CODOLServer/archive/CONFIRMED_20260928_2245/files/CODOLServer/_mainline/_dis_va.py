"""Dump x86 disassembly from the decrypted runtime image by VA.

Usage:
  python -X utf8 CODOLServer/_mainline/_dis_va.py 0xB999C0:0xB99A70 0xB9A5FB:0xB9A630

Image: _dyn100_run_20260925_182324/live/image_best.bin, load base 0x400000.
Read-only analysis helper (no game interaction).
"""
import os
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
IMAGE = os.path.join(HERE, "_dyn100_run_20260925_182324", "live", "image_best.bin")
BASE = 0x400000


def load():
    with open(IMAGE, "rb") as f:
        return f.read()


def main(argv):
    data = load()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    for spec in argv:
        if ":" in spec:
            a, b = spec.split(":", 1)
            start, end = int(a, 16), int(b, 16)
        else:
            start = int(spec, 16)
            end = start + 0x60
        print("=== %08X .. %08X ===" % (start, end))
        blob = data[start - BASE:end - BASE]
        for ins in md.disasm(blob, start):
            print("%08X  %-20s %s %s" % (ins.address, ins.bytes.hex(),
                                         ins.mnemonic, ins.op_str))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
