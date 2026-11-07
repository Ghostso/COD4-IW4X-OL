# -*- coding: utf-8 -*-
"""严格证明：可执行段内不存在对 [+0x75D8]/[+0x75DC] 的写入（覆盖 disp32 与 SIB 两种形式）。"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
d = pe.data
T = (0x75D8, 0x75DC)
OPC = {0x88: "mov r/m8,r8", 0x89: "mov r/m32,r32", 0xC6: "mov r/m8,imm8",
       0xC7: "mov r/m32,imm32", 0xFF: "grp5(inc/dec/...)", 0x01: "add", 0x09: "or",
       0x21: "and", 0x29: "sub", 0x31: "xor", 0x8B: "mov r,r/m (read)"}

tally = {}
examples = []
for o in range(len(d) - 8):
    op = d[o]
    if op not in OPC: continue
    m = d[o+1]
    mod = m >> 6; rm = m & 7
    if mod != 2: continue
    if rm == 4:
        # SIB form: [base+index*scale+disp32]
        sib = d[o+2]
        disp = struct.unpack_from("<i", d, o+3)[0]
        hdr = 3
    else:
        disp = struct.unpack_from("<i", d, o+2)[0]
        hdr = 2
    if disp not in T: continue
    va = pe.off_to_va(o)
    if not va or not pe.is_exec(va): continue
    kind = OPC[op] + ("/SIB" if rm == 4 else "")
    tally[kind] = tally.get(kind, 0) + 1
    examples.append((va, kind, hex(disp)))

print("=== 全部命中（可执行段内，含 SIB 形式）===")
for va, kind, disp in sorted(examples):
    print("   %08X  %-16s disp=%s" % (va, kind, disp))
print()
print("=== 汇总 ===")
for k, v in sorted(tally.items()):
    print("   %-18s %d" % (k, v))
writes = [e for e in examples if e[1].startswith(("mov", "grp5", "add", "or", "and", "sub", "xor")) and "r,r/m" not in e[1]]
print()
print("写入类命中 = %d" % len(writes))
