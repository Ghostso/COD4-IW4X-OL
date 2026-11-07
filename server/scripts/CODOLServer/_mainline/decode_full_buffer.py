"""完整解构客户端 11/4 发送缓冲区 —— 用写死的绝对偏移，不做启发式解析。

实测原始字节 (snap_003):
  0x3AC62E3B  00 00 00 02
  0x3AC62E3F  08 0b 00 00 00          service=11
  0x3AC62E44  0a 01 00 00 00 00 00 00 00   senderId=1
  0x3AC62E4D  10 50 6c 61 79 65 72 00  "Player\\0"
  0x3AC62E57  13 08 a6 00 00 00       outer blob len=166
  0x3AC62E5D  0a <u64 roomId>          payload 开始
"""
import json
import os
import struct
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


BASE = 0x3AC62E40
buf = read(BASE, 0x220)
if not buf:
    print('不可读')
    raise SystemExit(1)

print('=== 逐字段（写死偏移） ===')
print('  [+0x00] 08 u32 = %d   (service)' % struct.unpack_from('<I', buf, 1)[0])
print('  [+0x05] 0a u64 = %d   (senderId)' % struct.unpack_from('<Q', buf, 6)[0])
name_end = buf.find(b'\x00', 0x0E)
print('  [+0x0E] 10 str = %r  (terminator @ +0x%02X)' % (buf[0x0F:name_end], name_end))
p_138 = name_end + 1
print('  [+0x%02X] 13 08 u32 = %d  (outer blob len)'
      % (p_138, struct.unpack_from('<I', buf, p_138 + 2)[0]))
outer = struct.unpack_from('<I', buf, p_138 + 2)[0]
pstart = p_138 + 6
payload = buf[pstart:pstart + outer]
print('  payload 起点 +0x%02X, 共 %d B' % (pstart, len(payload)))

print()
print('=== payload 原始 ===')
for k in range(0, len(payload), 16):
    ch = payload[k:k + 16]
    print('  +%03X  %-47s  %s'
          % (k, ' '.join('%02x' % c for c in ch),
             ''.join(chr(c) if 32 <= c < 127 else '.' for c in ch)))

print()
print('=== payload 字段 ===')
j = 0
if payload[0] == 0x0A:
    print('  [0] 0a roomId = 0x%016X' % struct.unpack_from('<Q', payload, 1)[0])
    j = 9
depth = 0
while j + 6 <= len(payload) and depth < 6:
    depth += 1
    if payload[j] != 0x13 or payload[j + 1] != 0x08:
        print('  [%d] 非 13 08: %s' % (j, payload[j:j + 16].hex()))
        break
    ln = struct.unpack_from('<I', payload, j + 2)[0]
    print('  [%d] 13 08 blob len = %d' % (j, ln))
    if ln > len(payload) - j - 6:
        print('       越界')
        break
    sub = payload[j + 6:j + 6 + ln]
    for k in range(0, min(len(sub), 0x50), 16):
        print('        +%03X  %s' % (k, sub[k:k + 16].hex()))
    if len(sub) > 0x50:
        print('        ... 共 %d B' % len(sub))
    j += 6 + ln

lines = []
for k in range(0, len(buf), 16):
    lines.append('%08X  %s' % (BASE + k, ' '.join('%02x' % c for c in buf[k:k + 16])))
open(os.path.join(OUT, 'client_send_buffer.txt'), 'w', encoding='utf-8').write(
    '\n'.join(lines) + '\n')
cov.close()
f.close()
