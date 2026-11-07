#!/usr/bin/env python3
"""B11: 普查每个 UiCpp*::Init 体内的 push imm32 (找页号常量 2..154)."""
import struct
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
    ("UiCppMatchSelectView", 0x73DF20),
    ("UiCppItemListView", 0x748970),
    ("UiCppSuggestedLoadoutView", 0x748AE0),
    ("UiCppChallengesView", 0x748CB0),
    ("UiCppNewItems", 0x748B90),
    ("UiCppOnboarding", 0x7489E0),
]


def cstr(va, maxlen=80):
    f = va - VA
    if not (0 <= f < N):
        return None
    e = d.find(b"\x00", f)
    if e < 0 or e - f > maxlen:
        return None
    s = d[f:e]
    return s.decode("latin1") if s and all(32 <= c < 127 for c in s) else None


def body(entry, maxlen=0x6000):
    """线性反汇编到连续 2 个 cc (函数尾)."""
    f = entry - VA
    end = min(N, f + maxlen)
    code = d[f:end]
    ins = list(md.disasm(code, entry))
    out = []
    cc = 0
    for i in ins:
        if i.bytes[0] == 0xCC:
            cc += 1
            if cc >= 2:
                break
            continue
        cc = 0
        out.append(i)
    return out


print("%-26s %-9s %-7s %-7s %s" % ("View", "Init", "tot_push", "in2..154", "hits"))
grand = 0
for nm, va in VIEWS:
    ins = body(va)
    pushes = [i for i in ins if i.mnemonic == "push" and i.op_str.startswith("0x")]
    tot = len(pushes)
    hits = []
    for i in pushes:
        v = int(i.op_str, 16)
        if 2 <= v <= 154:
            hits.append((i.address, v))
    grand += len(hits)
    print("%-26s 0x%07X %-9d %-7d %s" % (nm, va, tot, len(hits),
          ", ".join("0x%X(=%d)" % (a, v) for a, v in hits) if hits else "-"))

print("\n总命中(push imm32 在 2..154) = %d" % grand)
print()
# 也报告每个 Init 的规模 (指令数) 与 是否调用注册器
for nm, va in VIEWS:
    ins = body(va)
    print("%-26s 指令数=%d" % (nm, len(ins)))

# 额外: 这些 Init 里有没有"取页号"的调用/getter? 找 push imm32 附近 mov [reg+off]
print("\n--- 各 Init 内所有 push imm32 (2..154) ---")
print("\n--- 扩展普查: 所有立即数指令 imm 在 2..154 ---")
md.detail = True
from capstone.x86 import X86_OP_IMM
for nm, va in VIEWS:
    ins = body(va)
    hits = []
    for i in ins:
        for op in i.operands:
            if op.type == X86_OP_IMM and 2 <= op.imm <= 154:
                hits.append((i.address, op.imm, i.mnemonic + " " + i.op_str))
    print("%-26s imm∈[2,154] 命中 %d" % (nm, len(hits)))
    for a, v, txt in hits:
        print("      0x%08X  %-8d %s" % (a, v, txt))

print("\n--- 对照: push 的大立即数(=字符串VA) 数量 ---")
for nm, va in VIEWS:
    ins = body(va)
    big = [i for i in ins if i.mnemonic == "push" and i.op_str.startswith("0x")
           and int(i.op_str, 16) > 0x400000]
    named = sum(1 for i in big if cstr(int(i.op_str, 16)))
    print("%-26s push(>0x400000)=%d  其中指向可打印串=%d" % (nm, len(big), named))
