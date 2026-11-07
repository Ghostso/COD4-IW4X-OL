"""在 createRoom 之后的快照里查 0x82E1458 前置拦截表。

0x634870:
    esi = [0x82E1458 + type*4]
    if (esi != 0) { call esi; return; }    <- 前置处理器
    else          { jmp [0x636f3c + type*4] }  <- 跳转表

早期转储里该表全 0。现在查 snap_003/004（建房后）。
"""
import json
import os
import struct

RUN = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\EARLIEST2_20261027_132645'
TABLE = 0x082E1458
N = 0x2F

for snap in ('snap_001', 'snap_002', 'snap_003', 'snap_004'):
    pj = os.path.join(RUN, snap + '.json')
    if not os.path.isfile(pj):
        continue
    meta = json.load(open(pj, encoding='utf-8'))
    lo = meta['lo']
    cov = open(os.path.join(RUN, snap + '_cover.bin'), 'r+b')
    f = open(os.path.join(RUN, snap + '.bin'), 'rb')
    off = TABLE - lo
    cov.seek(off)
    ok = cov.read(N * 4) == b'\x01' * (N * 4)
    print('=== %s t=%.1fs  覆盖=%s ===' % (snap, meta['t'], ok))
    if ok:
        f.seek(off)
        raw = f.read(N * 4)
        nz = 0
        for i in range(N):
            v = struct.unpack_from('<I', raw, i * 4)[0]
            if v:
                nz += 1
                print('    type 0x%02X -> 0x%08X' % (i, v))
        print('    非零 %d / %d' % (nz, N))
    cov.close()
    f.close()
    print()
