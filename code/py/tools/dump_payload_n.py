"""打印 payload#68（含 'Server'）的完整结构与上下文，作为信封范本。

用法: python -I tools/dump_payload_n.py <log> <index>
"""
import re
import sys

LOG = sys.argv[1]
IDX = int(sys.argv[2]) if len(sys.argv) > 2 else 68

txt = open(LOG, encoding='utf-8', errors='replace').read()
pays = []
for m in re.finditer(r'payload\((\d+)\):\s*((?:[0-9a-f]{2} )+)', txt):
    pays.append(bytes.fromhex(m.group(2).replace(' ', '')))

p = pays[IDX]
print('payload#%d  %d B' % (IDX, len(p)))
print('hex : %s' % p.hex())
print('ascii: %r' % p)
print()
print('逐字节:')
for i in range(0, len(p), 16):
    chunk = p[i:i + 16]
    hexs = ' '.join('%02x' % c for c in chunk)
    asc = ''.join(chr(c) if 32 <= c < 127 else '.' for c in chunk)
    print('  %04d  %-47s  %s' % (i, hexs, asc))
print()
# 尝试 protobuf-ish 解析: 10 <len> <str> / 13 08 <len> <data> / 08 <u32>
print('结构猜测:')
i = 0
while i < len(p):
    tag = p[i]
    if tag == 0x10 and i + 1 < len(p):
        ln = p[i + 1]
        s = p[i + 2:i + 2 + ln]
        print('  [%3d] 0x10 len=%d str=%r' % (i, ln, s))
        i += 2 + ln
    elif tag == 0x13 and i + 2 < len(p) and p[i + 1] == 0x08:
        ln = int.from_bytes(p[i + 2:i + 6], 'little')
        print('  [%3d] 0x13 08 blob len=%d' % (i, ln))
        i += 6 + ln
    elif tag == 0x08:
        v = int.from_bytes(p[i + 1:i + 5], 'little')
        print('  [%3d] 0x08 u32=%d' % (i, v))
        i += 5
    else:
        i += 1
