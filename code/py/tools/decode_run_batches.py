"""解码 11/4 各批次的实际内容，判断哪个是"准备"。

本轮 4 次:
    22:57:55  batch=63
    22:57:55  batch=21
    22:57:56  batch=16
    22:58:05  batch=240

按 room_protocol 的三层结构解出 body，看它们是什么操作。
"""
import re
import sys

LOG = sys.argv[1]


def parse_l2(raw):
    """raw = payload 明文: 0a <roomId> 13 08 <len> <declared> <body>"""
    if len(raw) < 16 or raw[0] != 0x0A or raw[9:11] != b'\x13\x08':
        return None
    rid = int.from_bytes(raw[1:9], 'little')
    ln = int.from_bytes(raw[11:15], 'little')
    inner = raw[15:15 + ln]
    if len(inner) != ln or len(inner) < 8:
        return None
    decl = int.from_bytes(inner[0:4], 'little')
    return {'room': rid, 'len': ln, 'declared': decl, 'body': inner[4:]}


txt = open(LOG, encoding='utf-8', errors='replace').read()
print('=== 11/4 上行批次逐条解码 ===')
for m in re.finditer(r'\[(\d\d:\d\d:\d\d)\][^\n]*\n?[^\n]*payload\((\d+)\):\s*((?:[0-9a-f]{2} )+)',
                     txt):
    ts = m.group(1)
    raw = bytes.fromhex(m.group(3).replace(' ', ''))
    r = parse_l2(raw)
    if not r:
        continue
    print('%s  roomId=0x%016X  body=%dB  declared=%d(=len-4:%s)'
          % (ts, r['room'], len(r['body']), r['declared'],
             r['declared'] == r['len'] - 4))
    print('           body = %s' % r['body'].hex())
    b = r['body']
    if len(b) >= 2:
        print('           首字节=0x%02X 子类型=0x%02X' % (b[0], b[1]))
    print()
