# -*- coding: utf-8 -*-
"""
_dyn100_fmt.py -- locate the code that formats "[%d] <lobby error text>"
and who supplies the number.

Focuses on the sites found by _dyn100_tbl.py H3:
   0x009EA9F2  mov eax, 0xde0ad0
   0x009EAA07  mov eax, 0xde0ad8
   0x009C2151  mov dword ptr [esi+0xd4], 0xdde694
and the popup registry consumers (@PLATFORM_POPUP_CONNECTION,
popup_connecting, Live_Frame).  Also scans for any true immediate operand
equal to a popup-registry pointer so the reader can see the dispatch.

Usage:
    python -X utf8 _dyn100_fmt.py <image_best.bin>
"""

import os
import struct
import sys

import capstone

MD = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
MD.detail = True

LO = 0x00400000
CODE_RANGES = [(0x00401000, 0x00994000), (0x00994000, 0x00CA8000)]

POINTS = [
    ("popup-format site A", 0x009EA9F2, 0x120, 0xC0),
    ("popup-format site B", 0x009EAA07, 0x120, 0xC0),
    ("DW_LIVE_CONNECTING slot", 0x009C2151, 0x140, 0x100),
    ("DW_LIVE_DISCONNECTED slot", 0x009C4F1D, 0x140, 0x100),
]

STRINGS = {
    "SF_UI_DW_LIVE_CONNECTING_FAILED": 0x00DE0640,
    "PLATFORM_POPUP_CONNECTION": 0x00DE68CC,
    "popup_connecting": 0x00DE6900,
    "Live_Frame": 0x00DE6910,
    "during_startup": 0x00DE68E8,
    "format_bracket_pct": 0x00DE0768,
}


def load(path):
    with open(path, "rb") as fh:
        return fh.read()


def show(blob, name, va, back, fwd):
    print("")
    print("=" * 78)
    print("%s  VA 0x%08X" % (name, va))
    print("=" * 78)
    start = va - back
    code = blob[start - LO:start - LO + back + fwd]
    for insn in MD.disasm(code, start):
        star = "  <<<" if insn.address <= va < insn.address + insn.size else ""
        print("    %08X  %-22s %s %s%s"
              % (insn.address, insn.bytes.hex(), insn.mnemonic,
                 insn.op_str, star))


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if not path:
        print(__doc__)
        return 1
    blob = load(path)
    print("image %s" % path)

    for name, va, back, fwd in POINTS:
        show(blob, name, va, back, fwd)

    print("")
    print("=" * 78)
    print("true immediate references to the popup registry strings")
    print("=" * 78)
    want = dict(STRINGS)
    hits = {k: [] for k in want}
    for start_va, end_va in CODE_RANGES:
        data = blob[start_va - LO:end_va - LO]
        for insn in MD.disasm(data, start_va):
            for op in insn.operands:
                if op.type != capstone.x86.X86_OP_IMM:
                    continue
                imm = int(op.imm) & 0xFFFFFFFF
                for k, v in want.items():
                    if imm == v:
                        hits[k].append((insn.address, insn.mnemonic, insn.op_str))
    for k, lst in hits.items():
        print("%-34s VA 0x%08X  refs=%d" % (k, want[k], len(lst)))
        for va, m, o in lst[:30]:
            print("    %08X  %s %s" % (va, m, o))

    # the "[%d]" format string lives at 0xDE0768; show its bytes
    print("")
    print("format string at 0x00DE0768:")
    off = 0x00DE0768 - LO
    print("   ", repr(blob[off:off + 64]))
    off2 = 0x00DE0AD0 - LO
    print("site A immediate target 0x00DE0AD0:")
    print("   ", repr(blob[off2:off2 + 96]))
    off3 = 0x00DE0AD8 - LO
    print("site B immediate target 0x00DE0AD8:")
    print("   ", repr(blob[off3:off3 + 96]))
    off4 = 0x00DDE694 - LO
    print("slot immediate target 0x00DDE694:")
    print("   ", repr(blob[off4:off4 + 64]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
