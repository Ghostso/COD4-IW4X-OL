"""在 snap_003/004 里找与房间 UI 状态相关的数据。

已知 UI 是 Scaleform。Scaleform 的 AS 变量名会以字符串形式
存在于 MovieDef 或注册表里。搜这些名字的**字符串副本**（不只是
0xDDD5xx 那一份），因为可能是动态构造的。

目标串（房间 UI 会读的状态）:
    room_id, roomIDHigh, roomIDLow, isroomhost, teamid, team,
    ready, Ready, isready, memberCount, maxPlayers
"""
import json
import os
import re

RUN = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\EARLIEST2_20261027_132645'
NEEDLES = [b'SetReadyState', b'GetReadyState', b'IsRoomHost', b'GetRoomInfo',
           b'isroomhost', b'memberCount', b'maxPlayers', b'roomIDHigh',
           b'roomIDLow', b'room_id']

snap = 'snap_003'
meta = json.load(open(os.path.join(RUN, snap + '.json'), encoding='utf-8'))
lo = meta['lo']
size = os.path.getsize(os.path.join(RUN, snap + '.bin'))
cov = open(os.path.join(RUN, snap + '_cover.bin'), 'r+b')
f = open(os.path.join(RUN, snap + '.bin'), 'rb')

print('扫描 %s (%.0f MB)' % (snap, size / 1048576))
hits = {n: [] for n in NEEDLES}
pos = 0
CH = 16 << 20
while pos < size:
    cov.seek(pos)
    if cov.read(1) != b'\x01':
        pos += CH
        continue
    f.seek(pos)
    data = f.read(min(CH, size - pos))
    if not data:
        break
    for n in NEEDLES:
        i = data.find(n)
        while i >= 0 and len(hits[n]) < 8:
            hits[n].append(lo + pos + i)
            i = data.find(n, i + 1)
    pos += max(1, len(data) - max(len(x) for x in NEEDLES))

print()
for n in NEEDLES:
    h = hits[n]
    print('%-16s %d 处 %s' % (n.decode(), len(h), [hex(x) for x in h[:6]]))

cov.close()
f.close()
