#!/usr/bin/env python3
"""Find instructions that reference a given struct displacement.

Usage:
  python -X utf8 CODOLServer/_mainline/_find_writes.py 0x4F4
  python -X utf8 CODOLServer/_mainline/_find_writes.py 0x4F4 --writes-only

Scans the decrypted runtime image. Read-only static analysis.
"""
from __future__ import annotations

import argparse
import os
import re

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "_dyn100_run_20260925_182324", "live",
                   "image_best.bin")
BASE = 0x400000


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("disp", help="displacement, e.g. 0x4F4")
    ap.add_argument("--writes-only", action="store_true")
    ap.add_argument("--limit", type=int, default=120)
    a = ap.parse_args()
    disp = int(a.disp, 16)

    data = open(IMG, "rb").read()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    needle = disp.to_bytes(4, "little")
    hits = []
    for m in re.finditer(re.escape(needle), data):
        va = BASE + m.start()
        lo = max(0, m.start() - 20)
        blob = data[lo:m.start() + 12]
        insns = list(md.disasm(blob, BASE + lo))
        # Find the instruction whose bytes contain the displacement.
        target = None
        for ins in insns:
            if ins.address <= va < ins.address + len(ins.bytes):
                target = ins
                break
        if target is None:
            continue
        text = f"{target.mnemonic} {target.op_str}"
        is_write = (target.mnemonic.startswith("mov")
                    and "[" in text and text.find("[") < text.find(","))
        if a.writes_only and not is_write:
            continue
        hits.append((target.address, is_write, insns))
        if len(hits) >= a.limit:
            break

    print(f"disp=0x{disp:X} refs={len(hits)}")
    for va, is_write, insns in hits:
        print("")
        print(f"VA 0x{va:08X} {'WRITE' if is_write else 'READ'}")
        for ins in insns:
            mark = "  <== HERE" if ins.address == va else ""
            print(f"  {ins.address:08X}  {ins.bytes.hex():<20} "
                  f"{ins.mnemonic} {ins.op_str}{mark}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
