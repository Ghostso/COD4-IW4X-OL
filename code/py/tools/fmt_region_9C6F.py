#!/usr/bin/env python3
"""0x9C6E00..0x9C7300 全部 NUL 串 —— 找"裸格式串"(不含事件名) 与 UIPage/UIClick 的配对格式.
同时: 全镜像找所有含 '${TIMESTAMP_PLACEHOLDER}' 的串, 与所有 '${...(%' 形态的格式串.
"""
import re, sys
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)

def p(s):
    sys.stdout.write(s.encode("ascii", "replace").decode("ascii") + "\n")

def strings(lo, hi, minlen=4):
    out = []
    i = lo
    while i < hi:
        if 32 <= d[i] < 127 and (i == 0 or not (32 <= d[i-1] < 127)):
            e = d.find(b"\x00", i, hi + 1)
            if e < 0:
                i += 1; continue
            if e - i >= minlen:
                out.append((i, d[i:e].decode("latin1")))
            i = e + 1
        else:
            i += 1
    return out

p("=== A) 0x9C6E00..0x9C7300 strings ===")
for off, s in strings(0x9C6E00, 0x9C7300):
    p("  0x%06X  %r" % (off, s))

p("")
p("=== B) all strings containing ${TIMESTAMP_PLACEHOLDER} ===")
for m in re.finditer(rb"\$\{TIMESTAMP_PLACEHOLDER\}", d):
    off = m.start()
    st = d.rfind(b"\x00", max(0, off - 200), off)
    en = d.find(b"\x00", off)
    p("  0x%06X  %r" % (st + 1, d[st + 1:en].decode("latin1")))

p("")
p("=== C) bare format strings: start with % or ${ and contain | ===")
seen = set()
for m in re.finditer(rb"(?:\x00)([%$][^|\x00]{0,40}(?:\|[^|\x00]{0,60}){2,})", d):
    off = m.start() + 1
    s = m.group(1).decode("latin1")
    if off in seen: continue
    seen.add(off)
    p("  0x%06X  %r" % (off, s[:220]))

p("")
p("=== D) strings containing ${ (macro usage), first 40 ===")
c = 0
for m in re.finditer(rb"\$\{[A-Z]", d):
    off = m.start()
    st = d.rfind(b"\x00", max(0, off - 120), off)
    en = d.find(b"\x00", off)
    p("  0x%06X  %r" % (st + 1, d[st + 1:en].decode("latin1")[:160]))
    c += 1
    if c >= 40: break
