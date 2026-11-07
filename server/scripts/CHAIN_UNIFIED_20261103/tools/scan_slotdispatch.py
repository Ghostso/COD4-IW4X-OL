"""扫"计算槽位"虚调用: call [reg + reg*4 + disp]  (= FF 54 <sib> disp8 / FF 94 <sib> disp32)。
   若某框架按运行时算出的槽位号派发, 就不会出现在 "mov rA,[rB+固定disp]" 形态里。

用法: python -I scan_slotdispatch.py
"""
import sys
from collections import Counter
sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from pe_map import load, va2off

P = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\UNPACKED_146\codoMP_unpacked_146.exe'
d, ib, secs = load(P)

REG = ['eax', 'ecx', 'edx', 'ebx', 'esp', 'ebp', 'esi', 'edi']
rows = []
# FF /2 mod=01 rm=100 (0x54): call [base+index*scale+disp8]
for op, modrm, dlen in ((0x54, None, 1), (0x94, None, 4)):
    for va_, vs, ra, rs in secs:
        n = min(vs, rs)
        if n <= 0 or ra <= 0:
            continue
        blob = d[ra:ra + n]
        i = 0
        while True:
            i = blob.find(bytes([0xFF, op]), i)
            if i < 0 or i + 3 > len(blob):
                break
            sib = blob[i + 2]
            scale = sib >> 6
            index = (sib >> 3) & 7
            base = sib & 7
            disp = blob[i + 3] if dlen == 1 else int.from_bytes(blob[i + 3:i + 7], 'little')
            rows.append((ib + va_ + i, scale, index, base, disp))
            i += 1

rows.sort()
print('call [base+index*scale+disp]  —— %d 处' % len(rows))
c = Counter((r[1], r[4]) for r in rows)
print('(scale,disp) 分布前 25: %s\n' % ', '.join('s%d/d0x%X×%d' % (s, dd, n) for (s, dd), n in c.most_common(25)))
for ca, sc, ix, bs, dd in rows[:60]:
    print('  %08X  call [%s + %s*%d + 0x%X]' % (ca, REG[bs], REG[ix], 1 << sc, dd))
