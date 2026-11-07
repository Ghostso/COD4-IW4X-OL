# -*- coding: utf-8 -*-
"""对 [0x76446B0] 做权威判定：线性反汇编全扫，按 读/写 分类。

比字节模式扫描可靠：能正确区分 `mov [0x76446b0], eax` 与
`mov edi, [eax+0x076446b0]`（后者的尾部字节会骗过模式匹配）。
"""
import capstone

EXE = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\UNPACKED_146\codoMP_unpacked_146.exe"
CODE_VA, CODE_RAW, CODE_LEN = 0x401000, 0x400, 0x008A689A
TARGET = 0x076446B0

d = open(EXE, 'rb').read()
seg = d[CODE_RAW:CODE_RAW + CODE_LEN]
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.detail = True

writes, reads, addrtaken = [], [], []
for ins in md.disasm(seg, CODE_VA):
    hit = False
    for op in ins.operands:
        if op.type == capstone.x86.X86_OP_MEM and (op.mem.disp & 0xFFFFFFFF) == TARGET:
            hit = True
            if ins.mnemonic.startswith(('mov', 'and', 'or', 'xor', 'add', 'sub', 'inc', 'dec')) \
               and op is ins.operands[0]:
                writes.append(ins)
            else:
                reads.append(ins)
        elif op.type == capstone.x86.X86_OP_IMM and (op.imm & 0xFFFFFFFF) == TARGET:
            hit = True
            addrtaken.append(ins)
    if hit and not any(o.type == capstone.x86.X86_OP_MEM and (o.mem.disp & 0xFFFFFFFF) == TARGET
                       for o in ins.operands) and not any(
            o.type == capstone.x86.X86_OP_IMM and (o.imm & 0xFFFFFFFF) == TARGET for o in ins.operands):
        pass

print("=== WRITES (%d) ===" % len(writes))
for i in writes:
    print("   %-9s %s %s" % (hex(i.address), i.mnemonic, i.op_str))
print("\n=== ADDRESS-TAKEN (imm, %d) ===" % len(addrtaken))
for i in addrtaken[:40]:
    print("   %-9s %s %s" % (hex(i.address), i.mnemonic, i.op_str))
print("\n=== READS (%d) ===" % len(reads))
for i in reads[:20]:
    print("   %-9s %s %s" % (hex(i.address), i.mnemonic, i.op_str))
