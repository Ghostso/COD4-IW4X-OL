"""单遍扫描: 枚举 "mov dword/word/byte ptr [reg+disp32], imm" 并直接给出立即数。

实现: 只扫一次, 对每个 0xC7 检查 modrm(mod=10, 有 disp32) 与 disp, 命中就取 imm。
O(镜像) 而不是 O(模式×镜像)。

用法:
  python -I scan_mem_a.py --dword 0x4d4
  python -I scan_mem_a.py --word  0x502
"""
import sys
from collections import Counter
sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from pe_map import load

P = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\UNPACKED_146\codoMP_unpacked_146.exe'
d, ib, secs = load(P)

mode, disp = 'dword', 0x4d4
args = sys.argv[1:]
for i, a in enumerate(args):
    if a in ('--byte', '--word', '--dword'):
        mode, disp = a[2:], int(args[i + 1], 0)

isz = {'byte': 1, 'word': 2, 'dword': 4}[mode]
disp_b = disp.to_bytes(4, 'little')

rows = []
for va_, vs, ra, rs in secs:
    n = min(vs, rs)
    if n <= 0 or ra <= 0:
        continue
    blob = d[ra:ra + n]
    base = ib + va_
    j = 0
    while True:
        j = blob.find(b'\xc7', j)
        if j < 0:
            break
        k = j + 1
        # 可选的操作数前缀 66 (仅 16 位形式)
        pre = 0
        if mode == 'word':
            if j > 0 and blob[j - 1] == 0x66:
                pre = 1
            else:
                j += 1
                continue
        else:
            if k < len(blob) and blob[k] == 0xc7:   # 不会发生, 保险
                pass
        if k >= len(blob):
            break
        modrm = blob[k]
        if (modrm & 0xC0) != 0x80:          # 只要 mod=10 → disp32
            j += 1
            continue
        rm = modrm & 7
        reg = (modrm >> 3) & 7
        off_disp = k + 1 + (1 if rm == 4 else 0)     # rm=4 → SIB
        if off_disp + 4 + isz > len(blob):
            break
        if blob[off_disp:off_disp + 4] != disp_b:
            j += 1
            continue
        imm = int.from_bytes(blob[off_disp + 4:off_disp + 4 + isz], 'little')
        sib = ''
        if rm == 4:
            s = blob[k + 1]
            sib = ' sib=%02x(scale=%d,idx=%d,base=%d)' % (s, s >> 6, (s >> 3) & 7, s & 7)
        rows.append((base + j - pre, mode, reg, rm, sib, imm))
        j = off_disp + 4 + isz

rows.sort()
print('mov %s [reg+0x%X], imm   —   %d 处' % (mode, disp, len(rows)))
c = Counter(r[5] for r in rows)
print('立即数分布: %s\n' % ', '.join('%d×%d' % (n, v) for v, n in sorted(c.items())))
for va, mo, reg, rm, sib, imm in rows:
    print('  %08X  = %-6d (0x%X)  reg=%d rm=%d%s' % (va, imm, imm, reg, rm, sib))
