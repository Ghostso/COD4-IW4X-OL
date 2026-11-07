# -*- coding: utf-8 -*-
"""归类 [0x76446B0] 的所有比较点：imm / 条件跳转 / 两侧被调者。

用途：判定 clientState 的高段(8/9/10)守卫的是"对局内逻辑"还是"控制台/日志/调试"，
从而区分两种解释：(a) 映像丢了写点  (b) 该地址是被复用的共享存储。
"""
import struct, sys, collections
import capstone

EXE = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\UNPACKED_146\codoMP_unpacked_146.exe"
CODE_VA, CODE_RAW, CODE_LEN = 0x401000, 0x400, 0x008A689A
ADR = struct.pack('<I', 0x076446B0)
ADR_VAL = 0x076446B0

d = open(EXE, 'rb').read()
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.detail = True


def va2off(va):
    return va - CODE_VA + CODE_RAW


def dis(va, n=12):
    off = va2off(va)
    out = []
    for ins in md.disasm(d[off:off + n * 8], va):
        out.append(ins)
        if len(out) >= n:
            break
    return out


def calls_in(insns):
    """收集这段里的直接 call 目标与字符串立即数(可疑提示串)"""
    calls, imms = [], []
    for ins in insns:
        if ins.mnemonic == 'call' and ins.operands and ins.operands[0].type == capstone.x86.X86_OP_IMM:
            calls.append(ins.operands[0].imm)
        if ins.mnemonic in ('push', 'mov') and ins.operands:
            for op in ins.operands:
                if op.type == capstone.x86.X86_OP_IMM and 0xDA0000 <= (op.imm & 0xFFFFFFFF) <= 0xE00000:
                    imms.append(op.imm & 0xFFFFFFFF)
    return calls, imms


# 1) 找所有比较点
sites = []
pat = bytes([0x83, 0x3D]) + ADR          # cmp dword [imm], imm8
i = 0
while True:
    i = d.find(pat, i)
    if i < 0:
        break
    if CODE_RAW <= i < CODE_RAW + CODE_LEN:
        v = d[i + 6]
        sites.append((i - CODE_RAW + CODE_VA, v - 0x100 if v >= 0x80 else v))
    i += 1
pat = bytes([0x81, 0x3D]) + ADR          # cmp dword [imm], imm32
i = 0
while True:
    i = d.find(pat, i)
    if i < 0:
        break
    if CODE_RAW <= i < CODE_RAW + CODE_LEN:
        sites.append((i - CODE_RAW + CODE_VA, struct.unpack_from('<i', d, i + 6)[0]))
    i += 1

print("comparison sites: %d" % len(sites))
print()

by_imm = collections.defaultdict(list)
for va, imm in sorted(sites):
    insns = dis(va, 4)                     # cmp + 条件跳转(可能先有 test 之类)
    jcc = None
    for ins in insns[1:]:
        if ins.mnemonic.startswith('j') and not ins.mnemonic.startswith('jmp'):
            jcc = ins
            break
    if jcc is None:
        continue
    tgt = jcc.operands[0].imm if jcc.operands and jcc.operands[0].type == capstone.x86.X86_OP_IMM else None
    fall = jcc.address + jcc.size
    c1, s1 = calls_in(dis(fall, 10))
    c2, s2 = (calls_in(dis(tgt, 10)) if tgt else ([], []))
    by_imm[imm].append((va, jcc.mnemonic, tgt, sorted(set(c1)), sorted(set(c2)), sorted(set(s1) | set(s2))))

for imm in sorted(by_imm):
    rows = by_imm[imm]
    print("=== imm == %-3d  (%d sites) ===" % (imm, len(rows)))
    for va, jc, tgt, c1, c2, st in rows[:60]:
        print("  %-9s %-4s -> %-9s  fall:%s   tgt:%s  strs:%s"
              % (hex(va), jc, hex(tgt) if tgt else '-',
                 [hex(x) for x in c1][:4], [hex(x) for x in c2][:4], [hex(x) for x in st][:3]))
    print()
