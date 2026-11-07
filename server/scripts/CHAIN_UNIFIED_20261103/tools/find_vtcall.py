"""枚举 "mov rA, [rB+disp] ; ... ; call rA" —— MSVC 在本镜像里**唯一**的虚调用形态。
   (不存在 `call [reg+disp]` 形式; 之前按字节模式扫 ff 5x 04 全是 imul 立即数的假阳性。)

用法:
  python -I find_vtcall.py 4                 # 只报 disp==4 的
  python -I find_vtcall.py --all             # 报所有 disp, 并统计分布
  python -I find_vtcall.py 4 --gap 12        # 允许 mov 与 call 之间最多 12 字节
"""
import sys
from collections import Counter
sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from pe_map import load, va2off
import capstone

P = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\UNPACKED_146\codoMP_unpacked_146.exe'
d, ib, secs = load(P)

want = None
gap = 12
limit = 400
lo = hi = None
args = sys.argv[1:]
i = 0
while i < len(args):
    a = args[i]
    if a == '--gap':
        gap = int(args[i + 1], 0); i += 2
    elif a == '--limit':
        limit = int(args[i + 1], 0); i += 2
    elif a == '--range':
        lo = int(args[i + 1], 0); hi = int(args[i + 2], 0); i += 3
    elif a == '--all':
        want = -1; i += 1
    elif a.startswith('--'):
        i += 1
    else:
        want = int(a, 0); i += 1

REG = ['eax', 'ecx', 'edx', 'ebx', 'esp', 'ebp', 'esi', 'edi']

# 收集所有 "call r32"(FF D0+r) 与 "jmp r32"(FF E0+r, 尾调用)
calls = []
for op in (0xD0, 0xE0):
    for r in range(8):
        pat = bytes([0xFF, op + r])
        for va_, vs, ra, rs in secs:
            n = min(vs, rs)
            if n <= 0 or ra <= 0:
                continue
            blob = d[ra:ra + n]
            i = blob.find(pat)
            while i >= 0:
                calls.append((ib + va_ + i, r))
                i = blob.find(pat, i + 1)

rows = []
# --- 形态 A: call [rA+disp]  (FF /2 mod=00 reg=2 rm=rA, disp8) ---
rowsA = []
_off = want if (want is not None and 0 <= want <= 0xFF) else None
if _off is not None:
    for rA in range(8):
        for va_, vs, ra, rs in secs:
            n = min(vs, rs)
            if n <= 0 or ra <= 0:
                continue
            blob = d[ra:ra + n]
            key2 = bytes([0xFF, 0x10 | rA, _off])
            i = blob.find(key2)
            while i >= 0:
                ca = ib + va_ + i
                for back in range(3, gap + 1):
                    mv = ca - back
                    om = va2off(secs, ib, mv)
                    if om is None:
                        continue
                    b = d[om:om + 8]
                    if len(b) < 3 or b[0] != 0x8B:
                        continue
                    modrm = b[1]
                    mod = modrm >> 6
                    rX = (modrm >> 3) & 7
                    rB = modrm & 7
                    if rX != rA:
                        continue
                    if mod == 0 and rB != 5:
                        rowsA.append((ca, mv, 0, rA, rB))
                    elif mod == 1:
                        rowsA.append((ca, mv, b[2], rA, rB))
                    break
                i = blob.find(key2, i + 1)

for ca, cr in calls:
    oa = va2off(secs, ib, ca)
    if oa is None:
        continue
    # 往前找 "mov rA, [rB+disp]" 且 rA == cr
    for back in range(3, gap + 1):
        mv = ca - back
        om = va2off(secs, ib, mv)
        if om is None:
            continue
        b = d[om:om + 8]
        if len(b) < 3 or b[0] != 0x8B:
            continue
        modrm = b[1]
        mod = modrm >> 6
        rA = (modrm >> 3) & 7
        rB = modrm & 7
        if rA != cr:
            continue
        if mod == 0:                       # [rB]
            if rB == 5:
                continue
            disp = 0
        elif mod == 1:                     # [rB+disp8]
            disp = b[2]
        elif mod == 2:                     # [rB+disp32]
            if len(b) < 6:
                continue
            disp = int.from_bytes(b[2:6], 'little')
        else:
            continue
        rows.append((ca, mv, disp, cr, rB))
        break

if want is not None and want >= 0:
    rows = [x for x in rows if x[2] == want]
    rowsA = [x for x in rowsA if x[2] == want]
if lo is not None:
    rows = [x for x in rows if lo <= x[1] < hi]
    rowsA = [x for x in rowsA if lo <= x[1] < hi]

c = Counter(x[2] for x in rows)
rows.sort()
rowsA.sort()
print('形态A  call [rA+disp] (先 mov rA,[rB]) —— %d 处' % len(rowsA))
for ca, mv, dsp, rA, rB in rowsA[:limit]:
    print('  call @%08X [%s+0x%X]   mov @%08X %s <- [%s]' % (ca, REG[rA], dsp, mv, REG[rA], REG[rB]))
print()
print('形态B  mov rA,[rB+disp]; call rA —— %d 处' % len(rows))
print('disp 分布(前 20): %s\n' % ', '.join('0x%X×%d' % (k, v) for k, v in c.most_common(20)))
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.skipdata = True
for ca, mv, disp, rA, rB in rows[:limit]:
    print('  mov @%08X  %s <- [%s+0x%X]      call @%08X' % (mv, REG[rA], REG[rB], disp, ca))
