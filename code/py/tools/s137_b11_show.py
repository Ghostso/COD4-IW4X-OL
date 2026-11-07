#!/usr/bin/env python3
"""B11: 各 UiCpp*::Init 前 ~34 条指令 (看小常量 push 的语境)."""
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)

VIEWS = [
    ("UiCppView", 0x7396F0),
    ("UiCppItemListView", 0x748970),
    ("UiCppNewItems", 0x748B90),
    ("UiCppOnboarding", 0x7489E0),
    ("UiCppSuggestedLoadoutView", 0x748AE0),
    ("UiCppChallengesView", 0x748CB0),
    ("UiCppMatchSelectView", 0x73DF20),
]


def cstr(va, maxlen=60):
    f = va - VA
    if not (0 <= f < N):
        return None
    e = d.find(b"\x00", f)
    if e < 0 or e - f > maxlen:
        return None
    s = d[f:e]
    return s.decode("latin1") if s and all(32 <= c < 127 for c in s) else None


for nm, va in VIEWS:
    print("=" * 70)
    print("%s @ 0x%08X" % (nm, va))
    code = d[va - VA:va - VA + 0x120]
    n = 0
    for ins in md.disasm(code, va):
        line = "  0x%08X  %-20s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str)
        for tok in ins.op_str.replace(",", " ").split():
            if tok.startswith("0x"):
                try:
                    s = cstr(int(tok, 16))
                except ValueError:
                    s = None
                if s:
                    line += "   ; '%s'" % s
        print(line)
        n += 1
        if n >= 34:
            break
