"""扫第二基址虚调用: "mov rA,[rB+4] ; ... ; call [rA+DISP]"。
   这是 C++ 多继承下走第二基址的调用形态 —— 引擎对象第二张表在 [引擎+4] (=0xD5AF9C),
   其 +0x0C 槽 = 0xBB45E0(引擎"连接")。find_vtcall 的形态A只认 `mov rA,[rB]`(mod=00),
   漏掉了 `mov rA,[rB+4]`(mod=01 disp=4) 这一种, 所以单写这个。

用法: python -I scan_secondbase.py 0x0C
"""
import sys
sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from pe_map import load, va2off

P = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\UNPACKED_146\codoMP_unpacked_146.exe'
d, ib, secs = load(P)

disp = int(sys.argv[1], 0) if len(sys.argv) > 1 else 0x0C
movdisp = 4
gap = 60
for i, a in enumerate(sys.argv):
    if a == '--movdisp':
        movdisp = int(sys.argv[i + 1], 0)
    if a == '--gap':
        gap = int(sys.argv[i + 1], 0)

REG = ['eax', 'ecx', 'edx', 'ebx', 'esp', 'ebp', 'esi', 'edi']

rows = []
for rA in range(8):
    pat = bytes([0xFF, 0x10 | rA, disp & 0xFF])
    for va_, vs, ra, rs in secs:
        n = min(vs, rs)
        if n <= 0 or ra <= 0:
            continue
        blob = d[ra:ra + n]
        i = blob.find(pat)
        while i >= 0:
            ca = ib + va_ + i
            for back in range(4, gap + 1):
                mv = ca - back
                om = va2off(secs, ib, mv)
                if om is None:
                    continue
                b = d[om:om + 8]
                if len(b) < 3 or b[0] != 0x8B:
                    continue
                modrm = b[1]
                if ((modrm >> 3) & 7) != rA:
                    continue
                mod = modrm >> 6
                rB = modrm & 7
                dd = None
                if mod == 1:
                    dd = b[2]
                elif mod == 0:
                    dd = 0
                elif mod == 2 and len(b) >= 6:
                    dd = int.from_bytes(b[2:6], 'little')
                if dd == movdisp:
                    rows.append((ca, mv, rA, rB))
                    break
            i = blob.find(pat, i + 1)

rows.sort()
print('mov rA,[rB+0x%X] ; call [rA+0x%X]  —— %d 处' % (movdisp, disp, len(rows)))
for ca, mv, rA, rB in rows:
    print('  call @%08X [%s+0x%X]   mov @%08X %s <- [%s+0x%X]'
          % (ca, REG[rA], disp, mv, REG[rA], REG[rB], movdisp))
