"""在 snap_003(建房之后, t=89s) 里重查推送路由表 0xE376C08..0xE37B7A8。

flat 布局: lo=0x10000 起, 连续内存镜像(覆盖段见 cover.bin)。
用 cover 判断某 VA 是否被覆盖, 再按偏移取值。
"""
import json
import os
import struct
import sys

RUN = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\EARLIEST2_20261027_132645'

for snap in ('snap_003', 'snap_004'):
    cov_p = os.path.join(RUN, snap + '_cover.bin')
    bin_p = os.path.join(RUN, snap + '.bin')
    meta_p = os.path.join(RUN, snap + '.json')
    if not (os.path.isfile(cov_p) and os.path.isfile(bin_p)):
        print(snap, 'missing')
        continue
    meta = json.load(open(meta_p, encoding='utf-8'))
    lo = meta['lo']
    cover = open(cov_p, 'rb').read()
    print('=== %s  t=%.1fs  lo=0x%X  cover=%d B ==='
          % (snap, meta['t'], lo, len(cover)))

    def covered(va, n=1):
        off = va - lo
        return 0 <= off and off + n <= len(cover) and cover[off:off + n] == b'\x01' * n

    f = open(bin_p, 'rb')

    def read(va, n):
        if not covered(va, n):
            return None
        f.seek(va - lo)
        return f.read(n)

    START, END, STRIDE, DELTA = 0x0E376C08, 0x0E37B7A8, 0x25D0, 0x25B8
    # 表只有 2 个 stride 就到底了(END-START = 0x4BA0 < 2*0x25D0)
    esi = START
    hits = []
    while esi < END:
        entry = esi - DELTA
        raw = read(entry, 0x20)
        h = read(esi, 4)
        if raw and h:
            f1, f2 = raw[0], raw[1]
            svc, task = struct.unpack_from('<II', raw, 0x10)
            handler = struct.unpack('<I', h)[0]
            if (f1, f2) != (0, 0) or handler:
                hits.append((esi, f1, f2, svc, task, handler))
        else:
            hits.append((esi, None, None, None, None, None))
        esi += STRIDE

    for esi, f1, f2, svc, task, h in hits:
        if f1 is None:
            print('  esi=0x%08X  (未覆盖/不可读)' % esi)
        else:
            print('  esi=0x%08X flags=(%d,%d) service=%d task=%d handler=0x%08X'
                  % (esi, f1, f2, svc, task, h))
    f.close()
    print()
