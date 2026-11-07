"""把房间对象结构对照到推送信封: 客户端收到的信封里，什么字段会落进
房间对象的 +0x00/+0x04 (roomId 低/高)?

已知房间对象 (snap_003, createRoom 之后):
    +000  roomId_lo   (0x55667788)
    +004  roomId_hi   (0x11223344)
    +008  0
    +00C  0x0101      (flag1=1, flag2=1)
    +010  1
    +014  0x56E
    +018  0x41A
    +01C  0

而 0x7E79C0 校验的是 [obj+8] / [obj+0xc] —— 注意这里是 +8/+0xC，
不是 +0/+4。说明 0x7E79C0 的 obj 是**另一个对象**（偏移不同）。

本脚本: 在快照里找所有 "开头就是 roomId_lo, roomId_hi" 的结构，
列出它们的完整布局，从而看清有几种"房间对象形态"。
"""
import json
import os
import struct

RUN = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\EARLIEST2_20261027_132645'
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


needle = struct.pack('<II', 0x55667788, 0x11223344)   # lo, hi
hits = []
size = os.path.getsize(os.path.join(RUN, snap + '.bin'))
pos = 0
while pos < size:
    cov.seek(pos)
    if cov.read(1) != b'\x01':
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
    pos += max(1, len(data) - 8)

print('"roomId_lo, roomId_hi" 相邻出现 %d 处' % len(hits))
for va in hits:
    d = read(va, 0x40)
    if not d:
        print('  0x%08X 不可读' % va)
        continue
    w = struct.unpack_from('<16I', d, 0)
    print('0x%08X' % va)
    print('   +000 %08X %08X %08X %08X   (roomId lo,hi then flags)' % w[0:4])
    print('   +010 %08X %08X %08X %08X' % w[4:8])
    print('   +020 %08X %08X %08X %08X' % w[8:12])
    print()

print()
print('=== 反向: roomId_hi, roomId_lo (高在前) ===')
needle2 = struct.pack('<II', 0x11223344, 0x55667788)
hits2 = []
pos = 0
while pos < size:
    cov.seek(pos)
    if cov.read(1) != b'\x01':
        pos += 1 << 20
        continue
    f.seek(pos)
    data = f.read(min(8 << 20, size - pos))
    if not data:
        break
    i = data.find(needle2)
    while i >= 0:
        hits2.append(lo + pos + i)
        i = data.find(needle2, i + 1)
    pos += max(1, len(data) - 8)
print('  出现 %d 处: %s' % (len(hits2), [hex(h) for h in hits2[:10]])
      )

cov.close()
f.close()
