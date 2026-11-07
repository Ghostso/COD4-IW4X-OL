"""单遍扫描 "mov word ptr [reg+disp32], r16"  (66 89 <modrm mod=10> <disp32>)。
   c7 形式(立即数)由 scan_mem_a.py 管; 这个管寄存器源。
   usage: python -I scan_mem_r.py --word 0x502
"""
import sys
from collections import Counter
sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from pe_map import load

P = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\UNPACKED_146\codoMP_unpacked_146.exe'
d, ib, secs = load(P)

disp = 0x502
size = 2
opcode = 0x89          # mov r/m, r
for i, a in enumerate(sys.argv):
    if a == '--word':
        disp, size, opcode = int(sys.argv[i + 1], 0), 2, 0x89
    if a == '--dword':
        disp, size, opcode = int(sys.argv[i + 1], 0), 4, 0x89
    if a == '--dword-imm-reg':   # mov reg, [reg+disp]  (8B ..) 只在需要时用
        disp, size = int(sys.argv[i + 1], 0), 4

opsize = b'\x66' if size == 2 else b''
disp_b = disp.to_bytes(4, 'little')
REG16 = ['ax', 'cx', 'dx', 'bx', 'sp', 'bp', 'si', 'di']

rows = []
for va_, vs, ra, rs in secs:
    n = min(vs, rs)
    if n <= 0 or ra <= 0:
        continue
    blob = d[ra:ra + n]
    base = ib + va_
    pat = opsize + bytes([opcode])
    j = 0
    while True:
        j = blob.find(pat, j)
        if j < 0:
            break
        k = j + len(pat)
        if k >= len(blob):
            break
        modrm = blob[k]
        if (modrm & 0xC0) != 0x80:
            j += 1
            continue
        rm = modrm & 7
        reg = (modrm >> 3) & 7
        off_disp = k + 1 + (1 if rm == 4 else 0)
        if off_disp + 4 > len(blob):
            break
        if blob[off_disp:off_disp + 4] != disp_b:
            j += 1
            continue
        rows.append((base + j, reg, rm))
        j = off_disp + 4

rows.sort()
print('mov %s [reg+0x%X], %s   —   %d 处'
      % ('word' if size == 2 else 'dword', disp, REG16[rows[0][1]] if rows else 'r16', len(rows)))
c = Counter(r[1] for r in rows)
print('源寄存器分布: %s\n' % ', '.join('%s×%d' % (REG16[r], n) for r, n in sorted(c.items())))
for va, reg, rm in rows:
    print('  %08X  ← %s' % (va, REG16[reg]))
