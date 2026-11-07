"""三连形态: mov rC,[rB+OFF1] ; mov rA,[rC+OFF2] ; call rA
   = C++ 多继承"走第二基址"最常见的 MSVC 产物
     (第二张表存在 [obj+4]，其 +0x0C 槽 = 引擎 connect 0xBB45E0)。

用法: python -I scan_2base_reg.py --off1 4 --off2 0x0C
"""
import sys
sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from pe_map import load, va2off

P = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\UNPACKED_146\codoMP_unpacked_146.exe'
d, ib, secs = load(P)

off1, off2 = 4, 0x0C
gap = 24
for i, a in enumerate(sys.argv):
    if a == '--off1':
        off1 = int(sys.argv[i + 1], 0)
    if a == '--off2':
        off2 = int(sys.argv[i + 1], 0)

REG = ['eax', 'ecx', 'edx', 'ebx', 'esp', 'ebp', 'esi', 'edi']


def mov_from(b, dest_reg, base_reg, disp):
    """b[0..] 是否 == 'mov dest_reg, [base_reg+disp]' (mod=01/10, 无 SIB)"""
    if len(b) < 3 or b[0] != 0x8B:
        return False
    modrm = b[1]
    mod = modrm >> 6
    if mod not in (1, 2):
        return False
    if ((modrm >> 3) & 7) != dest_reg or (modrm & 7) != base_reg or base_reg == 4:
        return False
    dd = b[2] if mod == 1 else int.from_bytes(b[2:6], 'little')
    return dd == disp


rows = []
for rA in range(8):
    pat = bytes([0xFF, 0xD0 + rA])
    for va_, vs, ra, rs in secs:
        n = min(vs, rs)
        if n <= 0 or ra <= 0:
            continue
        blob = d[ra:ra + n]
        i = blob.find(pat)
        while i >= 0:
            ca = ib + va_ + i
            for back in range(3, gap):
                mv2 = ca - back
                o2 = va2off(secs, ib, mv2)
                if o2 is None:
                    continue
                b2 = d[o2:o2 + 8]
                if len(b2) < 3 or b2[0] != 0x8B:
                    continue
                if ((b2[1] >> 3) & 7) != rA:
                    continue
                rC = b2[1] & 7
                if not mov_from(b2, rA, rC, off2):
                    continue
                # 再往前找 mov rC, [rB+off1]
                for back2 in range(3, gap):
                    mv1 = mv2 - back2
                    o1 = va2off(secs, ib, mv1)
                    if o1 is None:
                        continue
                    b1 = d[o1:o1 + 6]
                    for rB in range(8):
                        if mov_from(b1, rC, rB, off1):
                            rows.append((ca, mv2, mv1, rA, rC, rB))
                            break
                break
            i = blob.find(pat, i + 1)

rows.sort()
print('mov rC,[rB+0x%X] ; mov rA,[rC+0x%X] ; call rA  —— %d 处' % (off1, off2, len(rows)))
for ca, mv2, mv1, rA, rC, rB in rows[:80]:
    print('  call@%08X  [%s+0x%X] ; %s<-[%s+0x%X] ; %s<-[%s+0x%X]'
          % (ca, REG[rA], off2, REG[rA], REG[rC], off2, REG[rC], REG[rB], off1))
