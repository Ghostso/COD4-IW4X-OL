# -*- coding: utf-8 -*-
"""定位消息对象 +0x28（回调）与 +0x20（上下文）的消费点。"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
d = pe.data
R = "eax ecx edx ebx esp ebp esi edi".split()

def scan(disp, kinds):
    res = []
    for o in range(len(d) - 7):
        op = d[o]
        if op != 0xFF and op != 0x8B: continue
        m = d[o+1]
        if op == 0xFF:
            if (m & 0x38) != 0x10: continue        # /2 call
        mod = m >> 6
        rm = m & 7
        if mod == 1:
            off = struct.unpack_from("<b", d, o+2)[0]; hdr = 3
        elif mod == 2:
            if rm == 4: continue
            off = struct.unpack_from("<i", d, o+2)[0]; hdr = 6
        else:
            continue
        if rm == 4: continue
        if off != disp: continue
        va = pe.off_to_va(o)
        if va and pe.is_exec(va):
            res.append((va, R[rm], "call" if op == 0xFF else "mov-read"))
    return res

for disp in (0x28, 0x20):
    print("=== +0x%02X 的 call / mov-read 命中 ===" % disp)
    hits = sorted(scan(disp, None))
    calls = [h for h in hits if h[2] == "call"]
    reads = [h for h in hits if h[2] == "mov-read"]
    print("  call 类: %d" % len(calls))
    for va, reg, _ in calls[:30]:
        print("     %08X  call [%s+0x%02X]" % (va, reg, disp))
    print("  mov-read 类: %d" % len(reads))
    for va, reg, _ in reads[:20]:
        print("     %08X  mov ..., [%s+0x%02X]" % (va, reg, disp))
    print()
