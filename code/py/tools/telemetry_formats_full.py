#!/usr/bin/env python3
"""对 52 个事件名, 在其偏移处取完整 NUL 结尾串 (事件名|格式...) → 完整 事件→字段类型 表."""
E=r"E:\codol_re\client_image_20261027.bin"
d=open(E,"rb").read()
offs = {}
# 用正则直接从镜像重新定位(避免手抄偏移出错)
import re
for m in re.finditer(rb"([A-Z][A-Za-z0-9_]{2,40})\|(?=[%$][^|\x00]{0,40}\|)", d):
    name = m.group(1).decode("latin1")
    offs.setdefault(name, m.start())
print("重扫事件名 %d 种\n" % len(offs))
for name, off in sorted(offs.items(), key=lambda kv: kv[1]):
    e = d.find(b"\x00", off)
    s = d[off:e].decode("latin1")
    print("%-28s @0x%X  %s" % (name, off, s[:260]))
