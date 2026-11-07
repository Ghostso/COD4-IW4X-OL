"""按 body 长度分组，打印每类的实际内容与变化字节，确定消息类型。

产出: 每类一条代表性 hex + 变化位置的具体值。
"""
import glob
import os
import re

ROOT = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs'
ROOM = 0x1122334455667788

logs = glob.glob(os.path.join(ROOT, '**', 'lobby_srv.log'), recursive=True)
samples = []
for lp in logs:
    txt = open(lp, encoding='utf-8', errors='replace').read()
    for m in re.finditer(r'payload\((\d+)\):\s*((?:[0-9a-f]{2} )+)', txt):
        raw = bytes.fromhex(m.group(2).replace(' ', ''))
        if len(raw) < 16 or raw[0] != 0x0A or raw[9:11] != b'\x13\x08':
            continue
        rid = int.from_bytes(raw[1:9], 'little')
        if rid != ROOM:
            continue
        ln = int.from_bytes(raw[11:15], 'little')
        inner = raw[15:15 + ln]
        if len(inner) != ln or len(inner) < 8:
            continue
        samples.append(inner[4:])

by_len = {}
for b in samples:
    by_len.setdefault(len(b), []).append(b)

print('roomId=0x%016X 的样本 %d 条' % (ROOM, len(samples)))
print()
for ln in sorted(by_len):
    grp = by_len[ln]
    print('=== body = %d B  ×%d ===' % (ln, len(grp)))
    # 打印全部不同的形态
    uniq = []
    for b in grp:
        if b not in uniq:
            uniq.append(b)
    print('  不同形态 %d 种:' % len(uniq))
    for u in uniq[:6]:
        print('    %s' % u.hex())
    # 变化位置
    base = grp[0]
    diff = sorted({i for s in grp for i in range(min(len(base), len(s)))
                   if base[i] != s[i]})
    if diff:
        print('  变化字节位置: %s' % diff)
        for i in diff[:8]:
            vals = sorted({s[i] for s in grp})
            print('    [+%02d] 取值 %s' % (i, ['0x%02x' % v for v in vals]))
    else:
        print('  所有样本完全相同')
    print()
