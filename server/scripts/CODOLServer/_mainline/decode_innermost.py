"""解最内层房间数据块: 02 04 00 00 00 30 00 00 00 ...

已确认的三层:
    L1 信封  08 0b | 0a <sid> | 10 "Player" | 13 08 <166>
    L2 payload  0a <roomId> | 13 08 <145> | 08 01 00 00 00
    L3 blob  <u32 141> | 房间数据

现在解 L3 的 141 字节。
    02 04 00 00 00   <- ?
    30 00 00 00      <- 48
    e0 68 ab 5b ab 63 ab 03  <- ?
    00 00 00 00
    98 03 00 00      <- 920
    ...
"""
import json
import os
import struct
import sys

RUN = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\EARLIEST2_20261027_132645'
OUT = sys.argv[1] if len(sys.argv) > 1 else '.'

meta = json.load(open(os.path.join(RUN, 'snap_003.json'), encoding='utf-8'))
lo = meta['lo']
cov = open(os.path.join(RUN, 'snap_003_cover.bin'), 'r+b')
f = open(os.path.join(RUN, 'snap_003.bin'), 'rb')


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


BASE = 0x3AC62E40
buf = read(BASE, 0x200)
payload = buf[0x1C:0x1C + 166]
inner = payload[9 + 6:9 + 6 + 145]     # 跳过 roomId 和 13 08 len
print('L3 blob 长度 = %d' % len(inner))
declared = struct.unpack_from('<I', inner, 0)[0]
print('前 4 字节声明 = %d  (实际剩余 %d)' % (declared, len(inner) - 4))
body = inner[4:]
print('房间数据 = %d B' % len(body))
print()
for k in range(0, len(body), 16):
    ch = body[k:k + 16]
    print('  +%03X  %-47s  %s'
          % (k, ' '.join('%02x' % c for c in ch),
             ''.join(chr(c) if 32 <= c < 127 else '.' for c in ch)))
print()
print('=== 按 u32 序列 ===')
for k in range(0, len(body), 4):
    v = struct.unpack_from('<I', body, k)[0]
    if v:
        print('  +%03X  %10d  0x%08X' % (k, v, v))

cov.close()
f.close()
