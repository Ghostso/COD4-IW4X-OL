# -*- coding: utf-8 -*-
"""
_dyn100_dis.py -- disassemble the code around the lobby-string xrefs found
in the live pre-arm memory dump.

Pure disk analysis of an already-captured dump.  Nothing is launched.

Usage:
    python -X utf8 _dyn100_dis.py <image_best.bin> [<more.bin> ...]
"""

import os
import struct
import sys

import capstone

MD = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
MD.detail = False

LO = 0x00400000

# name -> (target VA, list of xref VAs)  (from the live dump xrefs.json)
XREFS = [
    ("SF_UI_DW_LIVE_DISCONNECTED", 0x00DBD888, [0x004AF3B6, 0x005704A2]),
    ("SF_UI_DW_LIVE_CERT_FAILED", 0x00DE09F0, [0x006839B1]),
    ("DW_DNS_ERROR", 0x00DE08D8, [0x00683178]),
    ("DW_ACCOUNT_ERROR", 0x00DE08F8, [0x006831B4]),
    ("dwLogonStart", 0x00DE08C8, [0x00683110]),
    ("TQOS_HOST_ied_tqos", 0x00DD98A0, [0x00692AB9]),
]


def load(path):
    with open(path, "rb") as fh:
        return fh.read()


def hexdump(blob, va, length=16):
    out = []
    for off in range(0, length, 16):
        chunk = blob[va - LO + off:va - LO + off + 16]
        if not chunk:
            break
        h = " ".join("%02X" % b for b in chunk)
        a = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        out.append("    %08X  %-47s  %s" % (va + off, h, a))
    return out


def dis_window(blob, xref_va, back=0x60, fwd=0x100):
    start = xref_va - back
    code = blob[start - LO:start - LO + back + fwd]
    lines = []
    for insn in MD.disasm(code, start):
        star = "  <<<=== XREF" if insn.address <= xref_va < insn.address + insn.size else ""
        lines.append("    %08X  %-24s %s %s%s"
                     % (insn.address, insn.bytes.hex(), insn.mnemonic,
                        insn.op_str, star))
    return lines


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    paths = sys.argv[1:]
    blobs = [(p, load(p)) for p in paths]
    print("loaded %d image(s):" % len(blobs))
    for p, b in blobs:
        print("  %s  size 0x%X" % (p, len(b)))
    blob = blobs[0][1]

    for name, tva, refs in XREFS:
        print("")
        print("=" * 78)
        print(name)
        print("  target VA 0x%08X   %d xref(s)" % (tva, len(refs)))
        print("=" * 78)
        for r in refs:
            print("")
            print("  xref VA 0x%08X (dump off 0x%X)" % (r, r - LO))
            print("  --- raw bytes around it ---")
            print("\n".join(hexdump(blob, r - 0x10, 0x30)))
            print("  --- disassembly (0x%08X .. ) ---" % (r - 0x60))
            print("\n".join(dis_window(blob, r)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
