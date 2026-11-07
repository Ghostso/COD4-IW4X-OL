#!/usr/bin/env python3
"""B7 决定性: 深层嵌套 24 个局域类, 看 cl 为 scope 11..24 实际发出的字符 (定 base 编码)."""
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WORK = os.path.join(os.environ["TEMP"], "s137_msvc_enc")
VCV = r"E:\BuildTools\VC\Auxiliary\Build\vcvars32.bat"
os.makedirs(WORK, exist_ok=True)

N = 26
L = ["struct Base{virtual ~Base(){}virtual void f(){}};", "void bar(void){"]
for i in range(1, N + 1):
    L.append("  " * i + "{")
    L.append("  " * (i + 1) + "struct S%02d:Base{virtual void f(){}} s%02d;" % (i, i))
for i in range(N, 0, -1):
    L.append("  " * i + "}")
L.append("}")
open(os.path.join(WORK, "t.cpp"), "w").write("\n".join(L) + "\n")

cmd = 'call %s >nul && cd /d %s && cl /c /nologo /EHsc /GR t.cpp >nul' % (VCV, WORK)
r = subprocess.run(cmd, shell=True, capture_output=True, timeout=300)
print("cl exit", r.returncode)
obj = open(os.path.join(WORK, "t.obj"), "rb").read()
pat = re.compile(rb"\?A[VU](S\d+)@\?([0-9A-P]+)([?@])")
rows = sorted(set((m.group(1).decode(), m.group(2).decode(), m.group(3).decode()) for m in pat.finditer(obj)))
print("%-6s %-8s %s" % ("class", "numsc", "sep"))
for k, num, sep in rows:
    print("%-6s %-8s %s" % (k, num, sep))
print("total", len(rows))
