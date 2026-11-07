"""在既有快照 snap_003/snap_004（createRoom 之后）里找 dwLobbyEventHandler 实例。

不用活进程、不用 ACE 绕过 —— 直接用 EARLIEST2_20261027_132645 的快照。
flat 布局: lo=0x10000 起连续镜像, cover.bin 标记覆盖。

目标:
  1. 搜 vtable 0x00DE07A4 的所有出现位置
  2. 对每个候选, 读 +0x18/+0x1c, 与 roomId 0x1122334455667788 比对
  3. 两快照对比, 看哪些字段变了
"""
import json
import os
import struct
import sys

RUN = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\EARLIEST2_20261027_132645'
VT = 0x00DE07A4
ROOM_HI = 0x11223344
ROOM_LO = 0x55667788

for snap in ('snap_003', 'snap_004'):
    bin_p = os.path.join(RUN, snap + '.bin')
    cov_p = os.path.join(RUN, snap + '_cover.bin')
    meta = json.load(open(os.path.join(RUN, snap + '.json'), encoding='utf-8'))
    if not (os.path.isfile(bin_p) and os.path.isfile(cov_p)):
        print(snap, '缺文件')
        continue
    lo = meta['lo']
    print('=== %s  t=%.1fs  pid=%d ===' % (snap, meta['t'], meta['pid']))
    cover = open(cov_p, 'r+b')
    f = open(bin_p, 'rb')

    def covered(va, n):
        off = va - lo
        if off < 0:
            return False
        cover.seek(off)
        return cover.read(n) == b'\x01' * n

    def read(va, n):
        if not covered(va, n):
            return None
        f.seek(va - lo)
        d = f.read(n)
        return d if len(d) == n else None

    # 分块扫全镜像找 vtable dword
    needle = struct.pack('<I', VT)
    hits = []
    CH = 8 << 20
    pos = 0
    size = os.path.getsize(bin_p)
    while pos < size:
        cover.seek(pos)
        if cover.read(1) != b'\x01':
            pos += CH
            continue
        f.seek(pos)
        data = f.read(min(CH, size - pos))
        if not data:
            break
        i = data.find(needle)
        while i >= 0:
            if (pos + i) % 4 == 0:
                hits.append(lo + pos + i)
            i = data.find(needle, i + 1)
        pos += len(data) - 4 if len(data) > 4 else len(data)

    print('  vtable 0x%08X 出现 %d 次' % (VT, len(hits)))
    for va in hits[:20]:
        d = read(va, 0x40)
        if not d:
            continue
        w = struct.unpack_from('<16I', d, 0)
        tag = ''
        if w[6] == ROOM_HI and w[7] == ROOM_LO:
            tag = '  ★ p18/p1c == roomId'
        elif w[6] or w[7]:
            tag = '  ← p18=0x%08X p1c=0x%08X' % (w[6], w[7])
        print('    0x%08X  w4=%08X w8=%08X wC=%08X p10=%08X p14=%08X p18=%08X p1c=%08X%s'
              % (va, w[1], w[2], w[3], w[4], w[5], w[6], w[7], tag))
    print()
    cover.close()
    f.close()

print()
print('=== 直接搜 roomId 值 0x%08X/0x%08X 成对出现的位置 ===' % (ROOM_HI, ROOM_LO))
for snap in ('snap_003', 'snap_004'):
    bin_p = os.path.join(RUN, snap + '.bin')
    cov_p = os.path.join(RUN, snap + '_cover.bin')
    meta = json.load(open(os.path.join(RUN, snap + '.json'), encoding='utf-8'))
    lo = meta['lo']
    cover = open(cov_p, 'r+b')
    f = open(bin_p, 'rb')
    pat = struct.pack('<II', ROOM_HI, ROOM_LO)     # 注意: p18=hi, p1c=lo
    pat2 = struct.pack('<Q', (ROOM_HI << 32) | ROOM_LO)
    print('  --- %s ---' % snap)
    for name, needle in (('hi,lo 相邻(u64小端 hi<<32|lo)', pat2), ('hi,lo 相邻(u32对)', pat)):
        hits = []
        pos = 0
        size = os.path.getsize(bin_p)
        while pos < size:
            cover.seek(pos)
            if cover.read(1) != b'\x01':
                pos += 1 << 20
                continue
            f.seek(pos)
            data = f.read(min(8 << 20, size - pos))
            if not data:
                break
            i = data.find(needle)
            while i >= 0:
                hits.append(lo + pos + i)
                i = data.find(needle, i + 1)
                if len(hits) > 30:
                    break
            pos += len(data) - 8 if len(data) > 8 else len(data)
        print('    %-32s %d 处: %s' % (name, len(hits), [hex(h) for h in hits[:10]]))
    cover.close()
    f.close()
