"""扫 `call [base + index]` / `call [base + index*scale + disp]` 的 **mod=00** 形态
   (FF 14 <sib>), 并按"所在函数是否取过引擎"过滤。
   之前 scan_slotdispatch.py 只覆盖了 mod=01(FF 54)/mod=10(FF 94), 漏了 mod=00。

用法: python -I scan_call_sib.py [--win 0x700]
"""
import sys
sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from pe_map import load, va2off

P = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\UNPACKED_146\codoMP_unpacked_146.exe'
d, ib, secs = load(P)

win = 0x700
for i, a in enumerate(sys.argv):
    if a == '--win':
        win = int(sys.argv[i + 1], 0)

REG = ['eax', 'ecx', 'edx', 'ebx', 'esp', 'ebp', 'esi', 'edi']
GE, SING = 0xBAC600, 0x643300
G331 = bytes.fromhex('c8c03103')
F1F0 = b''.join(bytes([0x8B, 0x80 | (r << 3) | rm]) + (0x1F0).to_bytes(4, 'little')
                for r in range(8) for rm in (0, 1, 2, 3, 5, 6, 7))


def acq(lo, hi):
    o1, o2 = va2off(secs, ib, lo), va2off(secs, ib, hi)
    if o1 is None or o2 is None or o2 <= o1:
        return []
    blob = d[o1:o2]
    h = []
    i = 0
    while True:
        i = blob.find(b'\xe8', i)
        if i < 0 or i + 5 > len(blob):
            break
        r = int.from_bytes(blob[i + 1:i + 5], 'little', signed=True)
        if (lo + i + 5 + r) & 0xFFFFFFFF in (GE, SING):
            h.append('call 0x%08X' % ((lo + i + 5 + r) & 0xFFFFFFFF))
        i += 1
    if G331 in blob:
        h.append('ref[0x331C0C8]')
    if F1F0 in blob:
        h.append('load[+0x1F0]')
    return h


rows = []
for va_, vs, ra, rs in secs:
    n = min(vs, rs)
    if n <= 0 or ra <= 0:
        continue
    blob = d[ra:ra + n]
    i = blob.find(b'\xff\x14')
    while i >= 0:
        if i + 3 <= len(blob):
            sib = blob[i + 2]
            sc, idx, base = sib >> 6, (sib >> 3) & 7, sib & 7
            rows.append((ib + va_ + i, sc, idx, base))
        i = blob.find(b'\xff\x14', i + 1)

print('call [base+index*scale] (mod=00) —— %d 处候选' % len(rows))
kept = []
for va, sc, idx, base in rows:
    h = acq(va - win, va)
    if h:
        kept.append((va, sc, idx, base, h))
print('其中窗口内含"取引擎"的: %d 处\n' % len(kept))
for va, sc, idx, base, h in kept[:60]:
    print('  %08X  call [%s + %s*%d]   前窗: %s'
          % (va, REG[base], REG[idx], 1 << sc, ' | '.join(h)))
