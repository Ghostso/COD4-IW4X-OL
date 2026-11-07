# -*- coding: utf-8 -*-
"""把覆盖 [0x76446B0] 的运行期分片按"采集批次目录"归组，读每片里该变量的值。

用途：把 clientState 的真实取值和实跑会话阶段对上——特别是"卡加载"那几次。
"""
import os
import struct
import collections

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
TARGET = 0x076446B0

sets = collections.defaultdict(list)
for dp, dn, fn in os.walk(ROOT):
    for n in fn:
        if not (n.startswith('r_') and n.endswith('.bin')):
            continue
        try:
            b_, l_ = n[2:-4].split('_')
            b = int(b_, 16)
            l = int(l_, 16)
        except Exception:
            continue
        if b <= TARGET < b + l:
            sets[dp].append((os.path.join(dp, n), b, l))

print("batches covering 0x%X : %d\n" % (TARGET, len(sets)))
for dp in sorted(sets):
    items = sets[dp]
    vals = collections.Counter()
    detail = []
    for p, b, l in sorted(items):
        try:
            with open(p, 'rb') as f:
                f.seek(TARGET - b)
                v = struct.unpack('<I', f.read(4))[0]
        except Exception as e:
            v = -1
        vals[v] += 1
        detail.append((os.path.basename(p), v))
    rel = os.path.relpath(dp, ROOT)
    print("=== %s   (%d dumps)" % (rel, len(items)))
    print("    values: %s" % dict(vals))
    for name, v in detail[:12]:
        print("      %-34s = %d" % (name, v))
    print()
