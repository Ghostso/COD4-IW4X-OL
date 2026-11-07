# -*- coding: utf-8 -*-
"""scanimm.py OFFSET IMM -- 扫描 `C7 <modrm> <disp8> <imm32>`（mov dword ptr [reg+off], imm）
与 `C6 <modrm> <disp8> <imm8>`；OFFSET/IMM 为十六进制。输出含所在函数线索。"""
import sys, io, os, struct
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from verify import P, MD

off = int(sys.argv[1], 16)
imm = int(sys.argv[2], 16)
imm4 = struct.pack('<I', imm & 0xFFFFFFFF)
imm1 = bytes([imm & 0xFF])
o = []
for va, vs, ra, rs, ch in P.secs:
    if not (ch & 0x20000000):
        continue
    buf = P.d[ra:ra + min(vs, rs)]
    n = len(buf)
    for i in range(n - 8):
        if buf[i] != 0xC7:
            continue
        modrm = buf[i + 1]
        if (modrm & 0xC0) != 0x40:      # mod=01 → disp8
            continue
        if buf[i + 2] != (off & 0xFF):
            continue
        if buf[i + 3:i + 7] != imm4:
            continue
        a = va + i
        try:
            ds = list(MD.disasm(P.rd(a, 8), a, count=1))
        except Exception:
            ds = []
        o.append('%08X  %s' % (a, (ds[0].mnemonic + ' ' + ds[0].op_str) if ds else '<bad>'))
o.append('--- total %d ---' % len(o))
txt = '\n'.join(o)
io.open(os.path.join(HERE, 'out', 'scanimm.txt'), 'w', encoding='utf-8').write(txt + '\n')
sys.stdout.write(txt.encode('ascii', 'backslashreplace').decode('ascii') + '\n')
