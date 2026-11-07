"""枚举对给定 VA 的**直接** E8 调用点(以及 call [mem] / jmp)。
   usage: python -I callers.py 0xBB54E0 [0xBB45E0 ...]
"""
import sys
sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from pe_map import load

P = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\UNPACKED_146\codoMP_unpacked_146.exe'
d, ib, secs = load(P)

targets = [int(a, 16) for a in sys.argv[1:]]

for t in targets:
    hits = []
    for va_, vs, ra, rs in secs:
        n = min(vs, rs)
        if n <= 0 or ra <= 0:
            continue
        blob = d[ra:ra + n]
        # E8 rel32 (call) 与 E9 rel32 (jmp, 尾调用); 另收 FF /4 abs? 见下
        for op, kind in ((0xE8, 'E8'), (0xE9, 'E9')):
            i = 0
            while True:
                i = blob.find(bytes([op]), i)
                if i < 0 or i + 5 > len(blob):
                    break
                va = ib + va_ + i
                r = int.from_bytes(blob[i + 1:i + 5], 'little', signed=True)
                if (va + 5 + r) & 0xFFFFFFFF == t:
                    hits.append((va, kind))
                i += 1
    hits.sort()
    print('0x%08X 直接 E8/E9 调用点: %d 个' % (t, len(hits)))
    for h, kind in hits:
        print('    %08X  (%s)' % (h, kind))
