"""按 `u32 total | flag | payload` 重新解释 11/4 容器, 并假设 payload 是位流。

关键样本 #7/#8 (20B):
    10 00 00 00 | 02 | 02 00 00 00 | 18 00 00 00 | d0 | 00 00 00 00 00 00 00
#9 只有末尾不同: d0 10 00 00 00 00 00 00

若 flag=0x02 是"容器内含子消息", 则后面应是 [u32 len][子消息] 序列。
试: 02 000000 之后, 18 000000 是什么? d0 是子消息首字节?

本脚本穷举几种切法并打印结果, 供人判读。
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

def u32(b, o):
    return int.from_bytes(b[o:o + 4], 'little') if o + 4 <= len(b) else None

for n, b in enumerate(batches, 1):
    total = u32(b, 0)
    if total != len(b) - 4:
        print('#%d 跳过(%d B, total=%s)' % (n, len(b), total))
        continue
    body = b[4:]
    print('=== #%d  %dB  body=%s ===' % (n, len(b), body.hex()))
    print('  flag = 0x%02X' % body[0])
    # 切法 A: flag | u32a | u32b | 剩余
    a, c = u32(body, 1), u32(body, 5)
    print('  切法A: flag | u32a=0x%X | u32b=0x%X | 剩余 %d B = %s'
          % (a or 0, c or 0, len(body) - 9, body[9:].hex()))
    # 切法 B: flag | u32len | 子消息(len 字节)
    ln = u32(body, 1)
    if ln is not None and 1 + 4 + ln <= len(body):
        print('  切法B: flag | len=%d | 子消息=%s' % (ln, body[5:5 + ln].hex()))
    print()
