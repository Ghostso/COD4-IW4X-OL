#!/usr/bin/env python3
"""Scan the live image for references to offsets inside the config block.

Read-only. Uses byte-level immediate scan (robust against disassembly desync).

Usage: python _cfg_scan_fields.py 0x331C5C0 0xD40
"""

import struct
import sys
from pathlib import Path

from capstone import CS_ARCH_X86, CS_MODE_32, Cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM

IMAGE_BASE = 0x400000
DEFAULT_IMAGE = (
    Path(__file__).resolve().parents[1]
    / "_mainline"
    / "_dyn100_run_20260925_182324"
    / "live"
    / "image_best.bin"
)

MD = Cs(CS_ARCH_X86, CS_MODE_32)
MD.detail = True


def main():
    base = int(sys.argv[1], 0)
    size = int(sys.argv[2], 0)
    limit = base + size
    image = Path(DEFAULT_IMAGE).read_bytes()

    found = {}
    # Capstone 5 requires an explicit length for large buffers; iterate in
    # windows so a desync or data island cannot silently truncate the scan.
    window = 0x40000
    for start in range(0, len(image), window):
        chunk = image[start:start + window]
        for insn in MD.disasm(chunk, IMAGE_BASE + start):
            hits = []
            for operand in insn.operands:
                if operand.type == X86_OP_MEM:
                    mem = operand.mem
                    if mem.base == 0 and mem.index == 0 and base <= mem.disp < limit:
                        hits.append(mem.disp)
                elif operand.type == X86_OP_IMM and base <= operand.imm < limit:
                    hits.append(operand.imm)
            for target in sorted(set(hits)):
                found.setdefault(target, []).append(
                    "%08X  %-22s %s %s"
                    % (insn.address, insn.bytes.hex(), insn.mnemonic, insn.op_str)
                )

    for target in sorted(found):
        print("OFFSET +0x%03X  VA 0x%08X" % (target - base, target))
        for line in found[target]:
            print("   " + line)
    print("distinct_offsets=%d" % len(found))
    print("total_refs=%d" % sum(len(v) for v in found.values()))


if __name__ == "__main__":
    main()
