"""打印 VA 处的一串 dword(用于读跳表/vtable/数据表)。
   usage: python -I dumpdw.py 0xBB26A4 5
          python -I dumpdw.py --abs 0xBB26A4 5      # 值按绝对 VA 解释
          python -I dumpdw.py --codes 0xBB258C 0xBB2590 0xBB25B7 0xBB2612
"""
import sys
sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from pe_map import load, va2off

P = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\UNPACKED_146\codoMP_unpacked_146.exe'
d, ib, secs = load(P)

va = int(sys.argv[1], 16)
n = int(sys.argv[2], 0)
off = va2off(secs, ib, va)
print('table @%08X  (%d entries)' % (va, n))
for i in range(n):
    v = int.from_bytes(d[off + i * 4: off + i * 4 + 4], 'little')
    print('  [%2d] +0x%02X  %08X' % (i, i * 4, v))
