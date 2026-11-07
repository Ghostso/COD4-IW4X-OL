"""在快照里搜 11/4 上行 payload 的实际字节模式。

实测上行 payload（服务端解出的明文）：
    0a 88 77 66 55 44 33 22 11 13 08 f5 00 00 00 f1 00 00 00 <245B batch>
即：
    0a <u64 roomId LE> 13 08 <u32 L> <u32 L-4> <L-4 字节数据>

这条字节流在客户端发送前一定完整存在于堆上。搜它，就能找到：
  - 缓冲区地址
  - 周围的对象结构
  - 长度字段的真实位置

搜两种模式：
  A. 完整前缀 0a <roomId> 13 08   (18 字节)
  B. 只要 0a <roomId>             (9 字节)
"""
import json
import os
import struct

RUN = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\EARLIEST2_20261027_132645'
ROOM = 0x1122334455667788

PATTERNS = {
    'A 完整前缀 (0a + u64 + 13 08)': b'\x0a' + struct.pack('<Q', ROOM) + b'\x13\x08',
    'B 仅 0a + u64': b'\x0a' + struct.pack('<Q', ROOM),
    'C 仅 u64 roomId': struct.pack('<Q', ROOM),
    'D 03 + u64 (若无 0a)': b'\x03' + struct.pack('<Q', ROOM),
}

for snap in ('snap_003', 'snap_004'):
    bin_p = os.path.join(RUN, snap + '.bin')
    cov_p = os.path.join(RUN, snap + '_cover.bin')
    meta = json.load(open(os.path.join(RUN, snap + '.json'), encoding='utf-8'))
    lo = meta['lo']
    size = os.path.getsize(bin_p)
    print('=== %s  t=%.1fs ===' % (snap, meta['t']))
    cov = open(cov_p, 'r+b')
    f = open(bin_p, 'rb')

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

    for name, needle in PATTERNS.items():
        hits = []
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
            while i >= 0 and len(hits) < 40:
                hits.append(lo + pos + i)
                i = data.find(needle, i + 1)
            pos += max(1, len(data) - len(needle))
        print('  %-32s %d 处' % (name, len(hits)))
        for va in hits[:12]:
            ctx = read(max(0, va - 16), 64)
            print('     0x%08X  ctx=%s' % (va, ctx.hex() if ctx else '?'))
    print()
    cov.close()
    f.close()
