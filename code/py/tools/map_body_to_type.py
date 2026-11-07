"""验证假设: 房间消息 body 的第 1 字节 = 分发表 type。

实测 body 形态:
    020200000018000000d0000000000000     首字节 0x02
    020200000008000000800800             首字节 0x02
    020600000030000000e068ab5b...        首字节 0x02
    020400000028000000b8180000...        首字节 0x02
    181c5a98d6145391cf01...              首字节 0x18
    4c000000a0100000...                  ?

若首字节是 type, 那么:
    0x02 -> 0x63495A   (分发表 type 0x02)
    0x18 -> 0x635D8F   (type 0x18)
它们在 47 项表里都存在。

问题: 大量 body 首字节都是 0x02, 但长度差异巨大(12/16/20/26/29/43/59/63/240)。
说明 0x02 只是外层 type, 真正的子类型在 body[1]。

本脚本: 统计所有公开 body 的首字节分布, 与分发表对照。
"""
import glob
import os
import re
import struct

ROOT = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs'
ROOM = 0x1122334455667788

VALID = {0x00, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A,
         0x0C, 0x0D, 0x0E, 0x0F, 0x10, 0x11, 0x12, 0x13, 0x14, 0x15,
         0x16, 0x17, 0x18, 0x1A, 0x1B, 0x1C, 0x1D, 0x1E, 0x1F, 0x20,
         0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x2B, 0x2C, 0x2D, 0x2E}

bodies = {}
for lp in glob.glob(os.path.join(ROOT, '**', 'lobby_srv.log'), recursive=True):
    txt = open(lp, encoding='utf-8', errors='replace').read()
    for m in re.finditer(r'payload\((\d+)\):\s*((?:[0-9a-f]{2} )+)', txt):
        raw = bytes.fromhex(m.group(2).replace(' ', ''))
        if len(raw) < 16 or raw[0] != 0x0A or raw[9:11] != b'\x13\x08':
            continue
        if int.from_bytes(raw[1:9], 'little') != ROOM:
            continue
        ln = int.from_bytes(raw[11:15], 'little')
        inner = raw[15:15 + ln]
        if len(inner) != ln or len(inner) < 8:
            continue
        b = inner[4:]
        bodies[b] = bodies.get(b, 0) + 1

print('roomId 样本 %d 条, 去重后 %d 种 body' % (sum(bodies.values()), len(bodies)))
print()
print('按首字节分组:')
by_first = {}
for b, c in bodies.items():
    by_first.setdefault(b[0], []).append((b, c))

for f in sorted(by_first):
    grp = by_first[f]
    total = sum(c for _, c in grp)
    ok = '✓ 在分发表内' if f in VALID else '✗ 不在分发表'
    print('  首字节 0x%02X  %3d 种 / %3d 次  %s' % (f, len(grp), total, ok))
    # 按 body[1] 再分
    if len(grp) <= 4:
        for b, c in grp[:4]:
            print('       ×%-3d %s' % (c, b.hex()))

print()
print('=== 首字节 0x02 的按 body[1] 细分 ===')
sub = {}
for b, c in bodies.items():
    if b[0] == 0x02 and len(b) > 1:
        sub.setdefault(b[1], []).append((b, c, len(b)))
for s in sorted(sub):
    grp = sub[s]
    lens = sorted({g[2] for g in grp})
    print('  02 %02X : %d 种, 长度 %s' % (s, len(grp), lens))
    for b, c, L in grp[:3]:
        print('       ×%-3d (%dB) %s' % (c, L, b.hex()))

print()
print('=== 从未出现的 type（分发表里有、上行里没有）===')
seen = set(by_first.keys())
print('  上行出现过: %s' % ['0x%02X' % x for x in sorted(seen)])
print('  分发表有:   %s' % ['0x%02X' % x for x in sorted(VALID)])
print('  ★ 未出现:   %s' % ['0x%02X' % x for x in sorted(VALID - seen)])
