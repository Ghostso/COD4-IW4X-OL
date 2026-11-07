#!/usr/bin/env python3
"""Extract tag-id literals from TenProxy.dll request handlers (read-only).

Usage: python _cfg_tenproxy_tags.py [path-to-TenProxy.dll]
"""

import sys
from pathlib import Path

import pefile
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
from capstone.x86 import X86_OP_IMM

MD = Cs(CS_ARCH_X86, CS_MODE_32)
MD.detail = True

DEFAULT = Path(__file__).resolve().parents[2] / "COD OL" / "TenProxy.dll"


def image_of(path):
    pe = pefile.PE(str(path), fast_load=True)
    return pe, pe.OPTIONAL_HEADER.ImageBase


def function_at(pe, image, va, limit=0x1200):
    rva = va - pe.OPTIONAL_HEADER.ImageBase
    offset = pe.get_offset_from_rva(rva)
    base = pe.OPTIONAL_HEADER.ImageBase
    # Re-base the raw slice so capstone reports real VAs.
    raw = image[offset:offset + limit]
    return list(MD.disasm(raw, va))


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    pe, base = image_of(path)
    image = path.read_bytes()
    candidates = [0x10007DA0, 0x10007EA0]
    for va in candidates:
        print("=== 0x%08X ===" % va)
        for insn in function_at(pe, image, va):
            if insn.mnemonic == "cmp":
                for operand in insn.operands:
                    if operand.type == X86_OP_IMM:
                        print(
                            "%08X  %-20s %s %s"
                            % (insn.address, insn.bytes.hex(), insn.mnemonic, insn.op_str)
                        )
            if insn.mnemonic == "ret":
                break


if __name__ == "__main__":
    main()
