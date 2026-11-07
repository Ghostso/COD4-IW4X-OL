# -*- coding: utf-8 -*-
"""_dyn100_site.py -- exact byte/disasm dump of a VA window."""

import sys

import capstone

LO = 0x00400000
MD = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)


def main():
    path, sva, back, fwd = sys.argv[1], int(sys.argv[2], 0), int(sys.argv[3], 0), int(sys.argv[4], 0)
    with open(path, "rb") as fh:
        b = fh.read()
    start = sva - back
    data = b[start - LO:start - LO + back + fwd]
    print("window 0x%08X .. 0x%08X" % (start, start + len(data)))
    for row in range(0, len(data), 16):
        c = data[row:row + 16]
        h = " ".join("%02X" % x for x in c)
        a = "".join(chr(x) if 32 <= x < 127 else "." for x in c)
        print("  %08X  %-47s  %s" % (start + row, h, a))
    print("--- disasm ---")
    for insn in MD.disasm(data, start):
        print("  %08X  %-24s %s %s" % (insn.address, insn.bytes.hex(),
                                        insn.mnemonic, insn.op_str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
