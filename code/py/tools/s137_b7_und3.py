#!/usr/bin/env python3
"""B7: undname 全部局域类, 抽取解码出的 scope label (权威解码)."""
import re
import subprocess
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
UND = r"E:\BuildTools\VC\Tools\MSVC\14.44.35207\bin\Hostx86\x86\undname.exe"
VA = 0x400000
d = open(E, "rb").read()

HEAD = re.compile(rb"\.\?A[VU][A-Za-z0-9_]+@\?[0-9A-P]+[?@]")


def cstr(f, maxlen=400):
    e = d.find(b"\x00", f)
    if e < 0 or e - f > maxlen:
        return None
    return d[f:e].decode("latin1")


hits = {}
for m in HEAD.finditer(d):
    s = cstr(m.start())
    if s and s not in hits:
        hits[s] = VA + m.start()

# 解析 name / digits / sep
P = re.compile(r"^\.\?A[VU]([A-Za-z0-9_]+)@\?([0-9A-P]+)([?@])")
rows = []
for s, va in hits.items():
    # 去掉首字节 '.' 再喂 undname (undname 需以 ? 开头)
    inp = s[1:] if s.startswith(".") else s
    try:
        r = subprocess.run([UND, inp], capture_output=True, text=True, timeout=20)
        out = (r.stdout or "") + (r.stderr or "")
    except Exception as ex:
        out = "ERR %s" % ex
    lab = re.findall(r"'::`?(\d+)'?::", out)
    lab2 = re.findall(r"`(\d+)'", out)
    m2 = P.match(s)
    rows.append((s, m2.group(1), m2.group(2), m2.group(3), lab or lab2, out.strip().splitlines()[-1] if out.strip() else ""))

print("%-12s %-6s %-3s %-10s %s" % ("name", "digits", "sep", "undname#", "decoded-tail"))
seen = {}
for s, nm, dg, sep, lab, tail in sorted(rows, key=lambda r: (r[2])):
    L = lab[0] if lab else "?"
    seen[dg] = (sep, L)
    print("%-40s ?%-5s %-3s %-10s %s" % (nm, dg, sep, L, tail[-70:]))

print()
print("=== digits -> (sep, undname label) ===")
for dg in sorted(seen):
    print("  ?%-5s %s" % (dg, seen[dg]))
