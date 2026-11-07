#!/usr/bin/env python3
"""B7: 精确扫描 单字符/双字符 -> undname 解码值, 两种终止结构."""
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UND = r"E:\BuildTools\VC\Tools\MSVC\14.44.35207\bin\Hostx86\x86\undname.exe"
CH = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def und(m):
    try:
        r = subprocess.run([UND, m], capture_output=True, text=True, timeout=20)
        out = ((r.stdout or "") + (r.stderr or "")).strip()
    except Exception as ex:
        return None
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    t = lines[-1] if lines else ""
    if "is :-" in t and '"?' in t:
        return None  # 未反解
    lab = re.findall(r"`(\d+)'::", t)
    if lab:
        return lab[0]
    if "anonymous namespace" in t:
        return "ANON"
    return "?(%s)" % t[-30:]


print("=== 结构 A: ?AUDummy@?<N>??bar@@YAXXZ   (即 client 形 A: @?<N>? ?bar) ===")
print("=== 结构 B: ?AUDummy@?<N>@??bar@@YAXXZ  (即 client 形 B: @?<N>@? ?bar) ===")
print("%-4s %-4s %-8s | %-4s %-8s" % ("N", "Asep", "A->", "Bsep", "B->"))
for c in CH:
    nA = "?AUDummy@?%s??bar@@YAXXZ" % c
    nB = "?AUDummy@?%s@??bar@@YAXXZ" % c
    print("%-4s %-4s %-8s | %-4s %-8s" % (c, "?", und(nA), "@", und(nB)))

print()
print("=== 双字符 ===")
for a in "0129AB":
    for b in "09ABLP":
        nA = "?AUDummy@?%s%s??bar@@YAXXZ" % (a, b)
        nB = "?AUDummy@?%s%s@??bar@@YAXXZ" % (a, b)
        ra, rb = und(nA), und(nB)
        print("  ?%s%s : A=%-6s B=%-6s" % (a, b, ra, rb))

print()
print("=== 三字符少数 ===")
for s in ("100", "999", "AAA", "CP0", "1A0"):
    nA = "?AUDummy@?%s??bar@@YAXXZ" % s
    nB = "?AUDummy@?%s@??bar@@YAXXZ" % s
    print("  ?%s : A=%-6s B=%-6s" % (s, und(nA), und(nB)))
