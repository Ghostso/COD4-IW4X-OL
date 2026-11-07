"""把客户端 11/4 上行批次按"容器 + 内层消息"两层拆开。

已知外层（8 次实测一致）:
    u32 total
    u8  0x02            <- 类型
    u32 ?               <- 恒 0x00000002 / 0x00000018 / 0x00000006
    u32 ?               <- 0x18 / 0x30 / 0xd0
    ...
本脚本按 total 切分所有子块, 逐个打印, 便于看"点了按钮之后哪几个字节变了"。
"""
import re
import sys

LOG = sys.argv[1]
txt = open(LOG, encoding='utf-8', errors='replace').read()

rows = []
for m in re.finditer(r'payload\((\d+)\):\s*((?:[0-9a-f]{2} )+)', txt):
    raw = bytes.fromhex(m.group(2).replace(' ', ''))
    i = raw.find(b'\x13\x08')
    if i < 0:
        continue
    ln = int.from_bytes(raw[i + 2:i + 6], 'little')
    b = raw[i + 6:i + 6 + ln]
    if len(b) == ln and ln >= 8:
        rows.append(b)

print('房间批次共 %d 条\n' % len(rows))
for n, b in enumerate(rows, 1):
    print('--- #%d  len=%d ---' % (n, len(b)))
    print('  ' + b.hex())
    off, guard = 0, 0
    while off + 4 <= len(b) and guard < 40:
        guard += 1
        v = int.from_bytes(b[off:off + 4], 'little')
        print('    [%3d] u32 = %d (0x%X)' % (off, v, v))
        off += 4
    print()
