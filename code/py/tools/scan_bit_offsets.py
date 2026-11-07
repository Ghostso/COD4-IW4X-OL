"""穷举位偏移：把客户端 11/4 上行批次在每一个 bit 偏移处按
`readBits(3)→应==3, readData(8)→type` 试解，看是否存在某个偏移能解出合法 type。

若存在，说明批次里嵌了一条位流消息，而且能定位它的精确起点。
"""
import re
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


def bits_at(data, bitpos, n):
    v = 0
    for k in range(n):
        p = bitpos + k
        byte, bit = p // 8, p % 8
        if byte >= len(data):
            return None
        if (data[byte] >> bit) & 1:
            v |= 1 << k
    return v


VALID_TYPES = {0x03, 0x0F, 0x10, 0x11, 0x14, 0x15, 0x17, 0x1A,
               0x1D, 0x1E, 0x1F, 0x25, 0x2D}

for n, b in enumerate(batches, 1):
    total = int.from_bytes(b[:4], 'little')
    if total != len(b) - 4:
        continue
    print('=== #%d  %dB  %s ===' % (n, len(b), b.hex()))
    found = []
    for bit in range(0, min(len(b) * 8 - 13, 160)):
        tag = bits_at(b, bit, 5)
        if tag != 3:
            continue
        typ = bits_at(b, bit + 5, 8)
        if typ in VALID_TYPES:
            found.append((bit, typ))
    if found:
        for bit, typ in found:
            print('    ★ bit %3d (byte %d.%d)  tag=3 type=0x%02X'
                  % (bit, bit // 8, bit % 8, typ))
    else:
        print('    无匹配')
    print()
