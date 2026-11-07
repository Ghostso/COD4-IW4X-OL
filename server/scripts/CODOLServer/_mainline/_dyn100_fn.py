# -*- coding: utf-8 -*-
"""
_dyn100_fn.py -- disassemble the real call sites that push the lobby UI
strings (found as 4-byte pointers in the live image).

Sites:
   0x007EF254  -> @SF_UI_DW_LIVE_CONNECTING_FAILED  (push 0xDE0640)
   0x005BE390  -> @PLATFORM_POPUP_CONNECTION        (push 0xDE68CC)
   0x005C64D3  -> @PLATFORM_POPUP_CONNECTION
   0x00808247  -> Live_Frame
   0x004FD929  -> @SF_UI_DW_LIVE_DISCONNECTED
   0x00621AA2  -> @SF_UI_DW_LIVE_DISCONNECTED
   0x007F317E  -> @SF_UI_DW_LIVE_CERT_FAILED

Usage:
    python -X utf8 _dyn100_fn.py <image_best.bin>
"""

import sys

import capstone

MD = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
MD.detail = False

LO = 0x00400000

SITES = [
    ("CONNECTING_FAILED", 0x007EF254, 0xA0, 0x90),
    ("PLATFORM_POPUP_CONNECTION a", 0x005BE390, 0x90, 0x90),
    ("PLATFORM_POPUP_CONNECTION b", 0x005C64D3, 0x90, 0x90),
    ("Live_Frame", 0x00808247, 0x90, 0x70),
    ("DISCONNECTED a", 0x004FD929, 0x80, 0x80),
    ("DISCONNECTED b", 0x00621AA2, 0x80, 0x80),
    ("CERT_FAILED", 0x007F317E, 0x80, 0x80),
]


def main():
    path = sys.argv[1]
    with open(path, "rb") as fh:
        b = fh.read()
    for name, va, back, fwd in SITES:
        print("")
        print("=" * 78)
        print("%s   site VA 0x%08X" % (name, va))
        print("=" * 78)
        start = va - back
        code = b[start - LO:start - LO + back + fwd]
        for insn in MD.disasm(code, start):
            star = "  <<<" if insn.address <= va < insn.address + insn.size else ""
            print("    %08X  %-24s %s %s%s"
                  % (insn.address, insn.bytes.hex(), insn.mnemonic,
                     insn.op_str, star))
    return 0


if __name__ == "__main__":
    sys.exit(main())
