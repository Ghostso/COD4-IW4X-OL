# -*- coding: utf-8 -*-
"""权威判定 [0x76446B0] 的读写：对每个字节出现点做回溯对齐解码。

线性扫描会被 .text 内嵌数据带偏；这里只对"确实出现该 4 字节"的位置
向前试 1..6 字节，用 capstone 找能把整条指令完整解出来的起点，
再按"目的操作数是不是内存"分类读写。
"""
import struct
import capstone

EXE = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\UNPACKED_146\codoMP_unpacked_146.exe"
CODE_VA, CODE_RAW, CODE_LEN = 0x401000, 0x400, 0x008A689A
TARGET = 0x076446B0
ADR = struct.pack('<I', TARGET)

d = open(EXE, 'rb').read()
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.detail = True

occ = []
i = CODE_RAW
while True:
    i = d.find(ADR, i)
    if i < 0:
        break
    if i < CODE_RAW + CODE_LEN:
        occ.append(i)
    i += 1
print("raw occurrences of the 4 bytes: %d" % len(occ))

real = []
for i in occ:
    found = None
    for k in range(1, 7):
        start = i - k
        if start < CODE_RAW:
            continue
        va = start - CODE_RAW + CODE_VA
        snip = d[start:i + 4 + 6]
        got = None
        for ins in md.disasm(snip, va):
            got = ins
            break
        if got is None:
            continue
        if got.size == k + 4:          # 恰好覆盖到地址末尾
            ops = got.operands
            if any(o.type == capstone.x86.X86_OP_MEM and (o.mem.disp & 0xFFFFFFFF) == TARGET for o in ops):
                found = got
                break
    if found is not None:
        real.append(found)

print("instructions that truly reference 0x%X: %d" % (TARGET, len(real)))
writes, reads, other = [], [], []
for ins in real:
    ops = ins.operands
    mem_ops = [o for o in ops if o.type == capstone.x86.X86_OP_MEM and (o.mem.disp & 0xFFFFFFFF) == TARGET]
    is_write = bool(mem_ops) and ops[0].type == capstone.x86.X86_OP_MEM
    (writes if is_write else reads).append(ins) if mem_ops or is_write else other.append(ins)
print()
print("=== WRITES (%d) ===" % len(writes))
for i in sorted(writes, key=lambda x: x.address):
    print("   %-9s %s %s" % (hex(i.address), i.mnemonic, i.op_str))
print()
print("=== READS (%d, 前 12) ===" % len(reads))
for i in sorted(reads, key=lambda x: x.address)[:12]:
    print("   %-9s %s %s" % (hex(i.address), i.mnemonic, i.op_str))
