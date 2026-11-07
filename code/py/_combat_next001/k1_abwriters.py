# -*- coding: utf-8 -*-
"""U2: 查找 [reg+0x3a048] / [reg+0x3a04c] 的写入点。"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
d = pe.data

TARGETS = (0x3A048, 0x3A04C, 0x278, 0xE360)
REGS = "eax ecx edx ebx esp ebp esi edi".split()

def scan(disp):
    res = []
    # mov [reg+disp32], reg  = 89 /r, mod=2 -> bytes: 89 modrm disp32
    for o in range(len(d) - 7):
        if d[o] != 0x89:
            continue
        modrm = d[o+1]
        if (modrm >> 6) != 2:
            continue
        rm = modrm & 7
        if rm == 4:
            continue
        v = struct.unpack_from("<i", d, o+2)[0]
        if v != disp:
            continue
        va = pe.off_to_va(o)
        if va and pe.is_exec(va):
            res.append(("mov", va, rm, (modrm >> 3) & 7))
    # mov dword [reg+disp32], imm32 = c7 /0, mod=2
    for o in range(len(d) - 10):
        if d[o] != 0xC7:
            continue
        modrm = d[o+1]
        if (modrm >> 6) != 2 or ((modrm >> 3) & 7) != 0:
            continue
        rm = modrm & 7
        if rm == 4:
            continue
        v = struct.unpack_from("<i", d, o+2)[0]
        if v != disp:
            continue
        va = pe.off_to_va(o)
        if va and pe.is_exec(va):
            imm = struct.unpack_from("<I", d, o+6)[0]
            res.append(("movimm", va, rm, imm))
    # movzx / mov byte [reg+disp32], reg  (88 /r)
    for o in range(len(d) - 7):
        if d[o] != 0x88:
            continue
        modrm = d[o+1]
        if (modrm >> 6) != 2:
            continue
        rm = modrm & 7
        if rm == 4:
            continue
        v = struct.unpack_from("<i", d, o+2)[0]
        if v != disp:
            continue
        va = pe.off_to_va(o)
        if va and pe.is_exec(va):
            res.append(("movb", va, rm, (modrm >> 3) & 7))
    # 读取点 mov reg,[reg+disp32] = 8b /r, mod=2
    for o in range(len(d) - 7):
        if d[o] != 0x8B:
            continue
        modrm = d[o+1]
        if (modrm >> 6) != 2:
            continue
        rm = modrm & 7
        if rm == 4:
            continue
        v = struct.unpack_from("<i", d, o+2)[0]
        if v != disp:
            continue
        va = pe.off_to_va(o)
        if va and pe.is_exec(va):
            res.append(("read", va, rm, (modrm >> 3) & 7))
    return res

for t in TARGETS:
    r = scan(t)
    writes = [x for x in r if x[0] != "read"]
    reads = [x for x in r if x[0] == "read"]
    print("=== disp +0x%X : writes=%d reads=%d ===" % (t, len(writes), len(reads)))
    for kind, va, rm, src in writes[:20]:
        print("   %08X %-7s [%s+0x%X], %s" % (va, kind, REGS[rm], t,
              hex(src) if kind == "movimm" else REGS[src] if isinstance(src, int) and src < 8 else src))
    for kind, va, rm, src in reads[:12]:
        print("   %08X read    %s <- [%s+0x%X]" % (va, REGS[src], REGS[rm], t))
