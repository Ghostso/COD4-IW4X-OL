"""AS_* 名字在内存中的副本，是在什么时刻出现的？

对比 snap_001(29s) / snap_002(61s) / snap_003(89s, createRoom 后) / snap_004(118s)：
若 0xE76Cxx 那块在 snap_001 就存在，说明是静态加载的（与大厅数据无关）；
若只在 snap_003 之后才有，说明是建房间后才构造的（可能依赖大厅数据）。
"""
import json
import os

RUN = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\EARLIEST2_20261027_132645'
NEEDLE = b'.?AVAS_SetReadyState@@'

for snap in ('snap_001', 'snap_002', 'snap_003', 'snap_004'):
    pj = os.path.join(RUN, snap + '.json')
    pb = os.path.join(RUN, snap + '.bin')
    pc = os.path.join(RUN, snap + '_cover.bin')
    if not (os.path.isfile(pj) and os.path.isfile(pb)):
        continue
    meta = json.load(open(pj, encoding='utf-8'))
    lo = meta['lo']
    size = os.path.getsize(pb)
    cov = open(pc, 'r+b')
    f = open(pb, 'rb')
    hits = []
    pos = 0
    while pos < size:
        cov.seek(pos)
        if cov.read(1) != b'\x01':
            pos += 1 << 20
            continue
        f.seek(pos)
        d = f.read(min(8 << 20, size - pos))
        if not d:
            break
        i = d.find(NEEDLE)
        while i >= 0 and len(hits) < 10:
            hits.append(lo + pos + i)
            i = d.find(NEEDLE, i + 1)
        pos += max(1, len(d) - len(NEEDLE))
    print('%s t=%.1fs  AS_SetReadyState 命中 %d 处: %s'
          % (snap, meta['t'], len(hits), [hex(h) for h in hits[:5]]))
    cov.close()
    f.close()
