#!/usr/bin/env python3
"""Dump a VA range of TenProxy.dll to a text file (ASCII only, read-only)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _tp_dis as T  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("start")
    ap.add_argument("end")
    ap.add_argument("out")
    args = ap.parse_args()
    pe, data, md = T.load(T.DEFAULT_DLL)
    imp = T.imports_by_va(pe)
    start, end = int(args.start, 16), int(args.end, 16)
    off = T.raw_for_rva(pe, start - T.IMAGE_BASE)
    blob = data[off:off + (end - start)]
    lines = []
    pos = 0
    while pos < len(blob):
        insn = next(md.disasm(blob[pos:], start + pos), None)
        if insn is None:
            pos += 1
            continue
        notes = T.annotate(pe, data, imp, insn)
        lines.append("0x%08X  %-24s %-8s %-34s%s" % (
            insn.address, insn.bytes.hex(), insn.mnemonic, insn.op_str,
            ("  ; " + " | ".join(notes)) if notes else ""))
        pos += insn.size
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="ascii")
    print("WROTE %s lines=%d" % (args.out, len(lines)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
