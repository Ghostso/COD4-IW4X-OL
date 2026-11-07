"""按 `u32 total | u8 flag | 若干 u32 字段 | 尾部数据` 拆解客户端 11/4 上行批次。

已知样本:
  16B: 10000000 02 02000000 18000000 d0 00000000000000
  20B: 10000000 02 02000000 18000000 d0 10000000 000000
  16B: 0c000000 02 02000000 08000000 800800
  63B: 3b000000 02 06000000 30000000 e068ab5bab63ab030000000050000000...
  21B: 11000000 18 1c5a98d6145391 cf01 6e580100000000

观察: u32[0] 比实际长度小 4 (total 字段不含自身)。
      16 结构: total=16, 但实际 20 字节 -> total 描述的是 total 之后的 16 字节。
"""
import re
import struct
import sys

LOG = sys.argv[1]
txt = open(LOG, encoding='utf-8', errors='replace').read()

batches = []
for m in re.finditer(r'payload\((\d+)\):\s*((?:[0-9a-f]{2} )+)', txt):
    raw = bytes.fromhex(m.group(2).replace(' ', ''))
    i = raw.find(b'\x13\x08')
    if i < 0:
        continue
    ln = int.from_bytes(raw[i + 2:i + 6], 'little')
    b = raw[i + 6:i + 6 + ln]
    if len(b) == ln and ln >= 8:
        batches.append(b)

for n, b in enumerate(batches, 1):
    total = int.from_bytes(b[:4], 'little')
    body = b[4:]
    print('=== #%d  %dB ===' % (n, len(b)))
    print('  total(不含自身)=%d  实际 body=%d  %s'
          % (total, len(body), 'OK' if total == len(body) else '★不符'))
    print('  %s' % b.hex())
    if total == len(body):
        # 逐字段
        print('  body[0]=flag=0x%02X' % body[0])
        rest = body[1:]
        # 尝试连续 u32
        vals = []
        for k in range(0, min(len(rest), 24), 4):
            if k + 4 <= len(rest):
                vals.append(int.from_bytes(rest[k:k + 4], 'little'))
        print('  后续 u32: %s' % [hex(v) for v in vals])
    print()
