"""解 6/5（MM 事件订阅）的请求，还原订阅了哪些事件。

已知 payload（10-27 实测）:
    08 00 00 00 00 | 08 14 00 00 00 | 01 | 01 00
       ^=0            ^=20(0x14)

这像是: [tag 08][u32 0] [tag 08][u32 20] [u8 1] [u8 1][u8 0]

本脚本: 把历史日志里所有 6/5 请求找出来，对比内容，
        看 20 个事件编号是否在别处列出。
"""
import glob
import os
import re

ROOT = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs'
logs = glob.glob(os.path.join(ROOT, '**', 'lobby_srv.log'), recursive=True)

found = []
for lp in logs:
    txt = open(lp, encoding='utf-8', errors='replace').read()
    # service=6 task=5
    for m in re.finditer(r'service=6 ver=\S+ task=5 declared=(\d+)\s*\n\s*payload\((\d+)\):\s*((?:[0-9a-f]{2} )+)',
                         txt):
        raw = bytes.fromhex(m.group(3).replace(' ', ''))
        run = os.path.basename(os.path.dirname(os.path.dirname(lp)))
        found.append((run, raw))

print('6/5 请求共 %d 条' % len(found))
uniq = {}
for run, raw in found:
    uniq.setdefault(raw, []).append(run)

print('去重后 %d 种:' % len(uniq))
for raw, runs in uniq.items():
    print()
    print('  hex = %s   (%d B, 出现 %d 次)' % (raw.hex(), len(raw), len(runs)))
    print('  来源: %s' % runs[:3])
    # 逐字段
    i = 0
    while i < len(raw):
        if raw[i] == 0x08 and i + 5 <= len(raw):
            v = int.from_bytes(raw[i + 1:i + 5], 'little')
            print('    [%2d] 08 u32 = %d' % (i, v))
            i += 5
        elif raw[i] == 0x0A and i + 9 <= len(raw):
            v = int.from_bytes(raw[i + 1:i + 9], 'little')
            print('    [%2d] 0a u64 = %d' % (i, v))
            i += 9
        elif raw[i] == 0x13 and i + 2 <= len(raw) and raw[i + 1] == 0x08:
            ln = int.from_bytes(raw[i + 2:i + 6], 'little')
            blob = raw[i + 6:i + 6 + ln]
            print('    [%2d] 13 08 blob len=%d: %s' % (i, ln, blob.hex()))
            i += 6 + ln
        else:
            print('    [%2d] 0x%02X' % (i, raw[i]))
            i += 1
