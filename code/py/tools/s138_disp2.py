#!/usr/bin/env python3
"""138: byte-pattern scan for accesses to a struct displacement.
disp encoded as u32 little endian. We look for modrm=mod10 reg/rm forms:
  mov r32,[r+disp32]   8B /r  (mod=10)
  lea r32,[r+disp32]   8D /r
  call [r+disp32]      FF /2
  mov [r+disp32],r32   89 /r
用法: s138_disp2.py <disp_hex>
"""
import sys
import struct

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)

from capstone import Cs, CS_ARCH_X86, CS_MODE_32
md = Cs(CS_ARCH_X86, CS_MODE_32)

disp = int(sys.argv[1], 0)
d32 = struct.pack("<I", disp)

ops = {}

def dis_at(va, before=0x14, after=0x10):
    f = va - VA
    s = max(0, f - before)
    code = d[s:f + after]
    out = []
    for ins in md.disasm(code, VA + s):
        mark = ">>" if ins.address == va else "  "
        out.append("   %s 0x%08X  %-14s %s %s" % (
            mark, ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
    return "\n".join(out)


pos = 0
hits = []
while True:
    i = d.find(d32, pos)
    if i < 0:
        break
    pos = i + 1
    # candidate modrm byte is 1..3 bytes before the disp
    for back in range(1, 5):
        m = i - back
        if m < 0:
            continue
        b = d[m]
        mod = (b >> 6) & 3
        if mod != 2:
            continue
        reg = (b >> 3) & 7
        rm = b & 7
        opb = d[m - 1] if m >= 1 else None
        op2 = d[m - 2] if m >= 2 else None
        # determine instruction start
        start = None
        kind = None
        if opb in (0x8B, 0x8D, 0x89, 0x8F, 0x03, 0x01, 0x2B, 0x29):
            start = m - 1
            kind = {0x8B: "mov_r_m", 0x8D: "lea", 0x89: "mov_m_r",
                    0x8F: "pop", 0x03: "add", 0x01: "add_m", 0x2B: "sub",
                    0x29: "sub_m"}[opb]
        elif opb == 0xFF:
            start = m - 1
            kind = {0: "inc", 1: "dec", 2: "call", 3: "callf", 4: "jmp",
                    6: "push"}.get(reg, "ff?%d" % reg)
        elif op2 == 0x0F and opb in (0xB6, 0xB7, 0xBE, 0xBF):
            start = m - 2
            kind = "movzx/sx"
        if start is None:
            continue
        va = VA + start
        hits.append((va, kind))
        break

# dedupe
seen = set()
for va, kind in sorted(hits):
    if va in seen:
        continue
    seen.add(va)
    print("\n--- 0x%08X  kind=%s" % (va, kind))
    print(dis_at(va))
print("\nTOTAL %d" % len(seen))
