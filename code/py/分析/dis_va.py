"""Disassemble / inspect a decrypted runtime image by VA.

Usage:
    python 分析/dis_va.py <image> <VA:VA|VA> [more...]
"""
import sys

import capstone

sys.stdout.reconfigure(encoding="utf-8")

BASE = 0x400000


def main():
    path = sys.argv[1]
    blob = open(path, "rb").read()
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = False
    print("image %s size 0x%X nonzero %d" % (path, len(blob), sum(1 for b in blob if b)))
    for spec in sys.argv[2:]:
        if ":" in spec:
            a, b = spec.split(":", 1)
            start, end = int(a, 16), int(b, 16)
        else:
            start = int(spec, 16)
            end = start + 0x80
        print()
        print("=== 0x%08X .. 0x%08X ===" % (start, end))
        chunk = blob[start - BASE:end - BASE]
        for ins in md.disasm(chunk, start):
            print(
                "0x%08X  %-22s %s %s"
                % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str)
            )


if __name__ == "__main__":
    main()
