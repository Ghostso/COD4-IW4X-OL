"""把客户端 11/4 上行的 245B 批次按 dwRoomMessage 位流规则解码。

假设: 批次 = 若干条消息的串联, 每条 =
    u32 长度(含自身?) | 头部 writeBits(3)=5位 + writeData(type,8) + 字段...

已知样本(实测):
  10000000 02 02000000 18000000 d0 00000000000000
  0c000000 02 02000000 08000000 800800
  3b000000 02 06000000 30000000 e068ab5bab63ab03...

先按 "u32 total | u8 flag | u32 a | u32 b | payload" 解,
再用位读器尝试把 payload 当作消息体读。

用法: python -I tools/decode_room_upstream.py <lobby_srv.log>
"""
import re
import struct
import sys

LOG = sys.argv[1]


class BitReader:
    def __init__(self, data):
        self.d = data
        self.pos = 0

    def read_bits(self):
        v = 0
        for i in range(5):
            byte, bit = self.pos // 8, self.pos % 8
            if byte >= len(self.d):
                raise EOFError('bits@%d' % self.pos)
            if (self.d[byte] >> bit) & 1:
                v |= 1 << i
            self.pos += 1
        return v

    def read_data(self, nbits):
        v = 0
        for i in range(nbits):
            byte, bit = self.pos // 8, self.pos % 8
            if byte >= len(self.d):
                raise EOFError('data@%d' % self.pos)
            if (self.d[byte] >> bit) & 1:
                v |= 1 << i
            self.pos += 1
        return v


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
    print('=== #%d  len=%d ===' % (n, len(b)))
    print('  raw: %s' % b.hex())
    total = int.from_bytes(b[:4], 'little')
    print('  u32[0] = %d (0x%X)   len=0x%X' % (total, total, len(b)))
    # 尝试把 b[4:] 当位流
    for off in (4, 5, 8):
        if off >= len(b):
            continue
        r = BitReader(b[off:])
        try:
            tag = r.read_bits()
            typ = r.read_data(8)
            ok = 'tag=%d(应为3) type=0x%02X' % (tag, typ)
        except EOFError:
            ok = '位读完'
        print('  从 +%d 起当位流: %s' % (off, ok))
    print()
