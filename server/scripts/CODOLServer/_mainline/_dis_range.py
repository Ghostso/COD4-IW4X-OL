"""Disassemble a VA range of the decrypted runtime image and filter opcodes.

Usage:
  python -X utf8 CODOLServer/_mainline/_dis_range.py 0xBA3700 0xBA3A10
  python -X utf8 CODOLServer/_mainline/_dis_range.py 0xBA3700 0xBA3A10 -0x2c
"""
from __future__ import annotations

import sys
from pathlib import Path

from capstone import CS_ARCH_X86, CS_MODE_32, Cs

IMAGE = Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
BASE = 0x400000


def parse_int(text: str) -> int:
    text = text.strip()
    neg = text.startswith("-")
    if neg:
        text = text[1:]
    return int(text, 16) * (-1 if neg else 1)


def main() -> int:
    start = parse_int(sys.argv[1])
    end = parse_int(sys.argv[2])
    filters = sys.argv[3:]
    image = IMAGE.read_bytes()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    for insn in md.disasm(image[start - BASE:end - BASE], start):
        if filters and not any(f in insn.op_str for f in filters):
            continue
        print("%08X  %-20s %-7s %s"
              % (insn.address, insn.bytes.hex(), insn.mnemonic, insn.op_str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
