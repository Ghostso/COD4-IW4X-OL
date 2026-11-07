"""读 0xE76C00 附近 —— 运行时构造的 Scaleform API 名表。

snap_003 实测（这些位置在静态转储 MEMDUMP 里不存在）：
    SetReadyState @ 0xE76C9F
    GetReadyState @ 0xE76C7F
    IsRoomHost    @ 0xE76C63
    GetRoomInfo   @ 0xE76B03
说明运行时在 0xE76B00~0xE76D00 一带拼出了这些名字。

把这一整块 dump 出来，看完整的 API 名清单。
"""
import json
import os
import sys

RUN = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\EARLIEST2_20261027_132645'
OUT = sys.argv[1] if len(sys.argv) > 1 else '.'

snap = 'snap_003'
meta = json.load(open(os.path.join(RUN, snap + '.json'), encoding='utf-8'))
lo = meta['lo']
cov = open(os.path.join(RUN, snap + '_cover.bin'), 'r+b')
f = open(os.path.join(RUN, snap + '.bin'), 'rb')


def read(va, n):
    off = va - lo
    if off < 0:
        return None
    cov.seek(off)
    if cov.read(n) != b'\x01' * n:
        return None
    f.seek(off)
    d = f.read(n)
    return d if len(d) == n else None


START = 0x00E76800
N = 0x600
d = read(START, N)
if not d:
    print('不可读')
    raise SystemExit(1)

print('=== 0x%08X 起的可打印串 ===' % START)
cur = bytearray()
cur_start = None
for i, c in enumerate(d):
    if 32 <= c < 127:
        if cur_start is None:
            cur_start = i
        cur.append(c)
    else:
        if len(cur) >= 3:
            print('  0x%08X  %s' % (START + cur_start, cur.decode()))
        cur = bytearray()
        cur_start = None
if len(cur) >= 3:
    print('  0x%08X  %s' % (START + cur_start, cur.decode()))

cov.close()
f.close()
