#!/usr/bin/env python3
"""遥测事件名全普查(不限"必须以 |% 开头再跟 |"):
所有 NUL 串, 形如 Name|... 且 Name 匹配 [A-Z][A-Za-z0-9_]{2,40},
且尾部像遥测(含 % 或 ${ 或为空/单串), 并且串位于已证实的模板区带内.
输出: 事件名 / 偏移 / 完整串 / 项数.
"""
import re, sys
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read(); N = len(d)

def out(s):
    sys.stdout.write(s.encode("ascii", "replace").decode("ascii") + "\n")

rows = []
i = 0
while i < N:
    if 32 <= d[i] < 127 and (i == 0 or not (32 <= d[i-1] < 127)):
        e = d.find(b"\x00", i)
        if e < 0: break
        s = d[i:e].decode("latin1")
        m = re.match(r"^([A-Z][A-Za-z0-9_]{2,40})\|(.*)$", s)
        if m:
            name, body = m.group(1), m.group(2)
            # 遥测判据: body 含 % 或 ${, 或 body 为空
            if ("%" in body) or ("${" in body) or body == "":
                rows.append((i, name, s))
        i = e + 1
    else:
        i += 1

# 去重: 同名取首次
seen = {}
for off, name, s in rows:
    if name not in seen: seen[name] = (off, s)

out("事件名串总数(含重复名) = %d ; 去重名 = %d" % (len(rows), len(seen)))
out("")
out("%-34s %8s %5s  %s" % ("event", "file", "items", "template"))
out("-" * 130)
for name, (off, s) in sorted(seen.items(), key=lambda kv: kv[1][0]):
    items = s.count("%") + 1
    out("%-34s 0x%06X %5d  %s" % (name, off, items, s[:200]))

out("")
out("=== 重复名的全部出现处(说明存在同名多模板) ===")
byname = {}
for off, name, s in rows:
    byname.setdefault(name, []).append((off, s))
for name, lst in sorted(byname.items()):
    if len(lst) > 1:
        out("  %s (%d 处)" % (name, len(lst)))
        for off, s in lst:
            out("      0x%06X  %s" % (off, s[:190]))
