#!/usr/bin/env python3
"""找 52 条模板串的引用点, 看布局: (a) 指针表 (name,fmt) 还是 (b) 逐个 push imm32.
同时列 0x9E1400..0x9E1640 的串, 判断 '仅格式无名字' 的三条是不是从别处拼的.
"""
import struct, re, sys
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read(); N = len(d)

def out(s):
    sys.stdout.write(s.encode("ascii", "replace").decode("ascii") + "\n")

tmpl = {}
for m in re.finditer(rb"([A-Z][A-Za-z0-9_]{2,40})\|(?=[%$][^|\x00]{0,40}\|)", d):
    name = m.group(1).decode("latin1"); off = m.start()
    if name in tmpl: continue
    tmpl[name] = off

out("%-30s %8s %s" % ("event", "strFile", "refs(4B LE ptr=file+0x400000)"))
out("-" * 80)
tab = []
for name, off in sorted(tmpl.items(), key=lambda kv: kv[1]):
    ptr = off + VA
    hits = [m.start() for m in re.finditer(re.escape(struct.pack("<I", ptr)), d)]
    out("%-30s 0x%06X %d %s" % (name, off, len(hits), [hex(h) for h in hits[:6]]))
    for h in hits: tab.append((h, name))

out("")
out("=== 引用点排序: 若成对相邻, 即为 (name,fmt) 指针表 ===")
for h, name in sorted(tab):
    out("  0x%06X  %s" % (h, name))

out("")
out("=== 0x9E1400..0x9E1640 串 ===")
i = 0x9E1400
while i < 0x9E1640:
    if 32 <= d[i] < 127 and (i == 0 or not (32 <= d[i-1] < 127)):
        e = d.find(b"\x00", i, 0x9E1700)
        if e < 0: break
        out("  0x%06X  %r" % (i, d[i:e].decode("latin1")[:200]))
        i = e + 1
    else:
        i += 1
