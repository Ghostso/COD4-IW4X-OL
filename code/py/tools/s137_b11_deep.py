#!/usr/bin/env python3
"""B11 扩展: 各 Init + 其 1-hop E8 callees 内所有 imm∈[2,154]."""
import struct
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_IMM

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

# code ranges
pe = struct.unpack_from("<I", d, 0x3C)[0]
nsec = struct.unpack_from("<H", d, pe + 6)[0]
opt = struct.unpack_from("<H", d, pe + 0x14)[0]
sh = pe + 0x18 + opt
CODE = []
for i in range(nsec):
    o = sh + i * 0x28
    vsz, va, rsz, raw = struct.unpack_from("<IIII", d, o + 8)
    fl = struct.unpack_from("<I", d, o + 36)[0]
    if fl & 0x20000000 or fl & 0x20:
        CODE.append((0x400000 + va, 0x400000 + va + max(vsz, rsz)))


def incode(va):
    return any(lo <= va < hi for lo, hi in CODE)


def cstr(va, mx=60):
    f = va - VA
    if not (0 <= f < N):
        return None
    e = d.find(b"\x00", f)
    if e < 0 or e - f > mx:
        return None
    s = d[f:e]
    return s.decode("latin1") if s and all(32 <= c < 127 for c in s) else None


def insns(entry, mx=0x4000):
    f = entry - VA
    if not incode(entry):
        return []
    out, cc = [], 0
    for i in md.disasm(d[f:min(N, f + mx)], entry):
        if i.bytes[0] == 0xCC:
            cc += 1
            if cc >= 2:
                break
            continue
        cc = 0
        out.append(i)
    return out


VIEWS = [("UiCppView", 0x7396F0), ("UiCppMatchSelectView", 0x73DF20), ("UiCppItemListView", 0x748970),
         ("UiCppSuggestedLoadoutView", 0x748AE0), ("UiCppChallengesView", 0x748CB0),
         ("UiCppNewItems", 0x748B90), ("UiCppOnboarding", 0x7489E0)]

for nm, va in VIEWS:
    base = insns(va)
    calls = sorted(set(struct.unpack_from("<i", d, i.address - VA + 1)[0] + i.address + 5
                       for i in base if i.mnemonic == "call" and i.op_str.startswith("0x")))
    calls = [c for c in calls if incode(c)]
    tot_hits = []
    for c in calls:
        for i in insns(c):
            for op in i.operands:
                if op.type == X86_OP_IMM and 2 <= op.imm <= 154:
                    tot_hits.append((c, i.address, op.imm, i.mnemonic + " " + i.op_str))
    print("%-26s Init指令=%d callees=%d  imm∈[2,154] 命中=%d" % (nm, len(base), len(calls), len(tot_hits)))
    for c, a, v, t in tot_hits:
        print("      callee=0x%08X  0x%08X  %-6d %s" % (c, a, v, t))
