#!/usr/bin/env python3
"""B7: 真编译 (cl.exe) 一个含 N 个局域类的函数, dumpbin 抽 mangled 名, 解码序号; 验证 10/11 边界."""
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WORK = os.path.join(os.environ["TEMP"], "s137_msvc_b7")
VCV = r"E:\BuildTools\VC\Auxiliary\Build\vcvars32.bat"
UND = r"E:\BuildTools\VC\Tools\MSVC\14.44.35207\bin\Hostx86\x86\undname.exe"
os.makedirs(WORK, exist_ok=True)

N = 24
L = ["struct Base{virtual ~Base(){}virtual void f(){}};", "void bar(void){"]
for i in range(1, N + 1):
    L.append("  struct L%02d:Base{virtual void f(){}} l%02d;" % (i, i))
L.append("}")
open(os.path.join(WORK, "t.cpp"), "w").write("\n".join(L) + "\n")

cmd = 'call %s >nul && cd /d %s && cl /c /nologo /EHsc /GR t.cpp >nul && dumpbin /symbols t.obj' % (VCV, WORK)
r = subprocess.run(cmd, shell=True, capture_output=True, timeout=300)
out = r.stdout.decode("latin1", "replace") + r.stderr.decode("latin1", "replace")
print("cl exit", r.returncode)

# 直接扫 obj 字节
obj = open(os.path.join(WORK, "t.obj"), "rb").read()
pat = re.compile(rb"\?A[VU]L\d+@\?[0-9A-P]+[?@]")
syms = sorted(set(m.group(0).decode("latin1") for m in pat.finditer(obj)))
print("抽到局域类符号 %d 条" % len(syms))
def und(m):
    rr = subprocess.run([UND, "." + m], capture_output=True, timeout=20)
    t = [x.strip() for x in rr.stdout.decode("latin1", "replace").splitlines() if x.strip()]
    lab = re.findall(r"`(\d+)'::", t[-1]) if t else []
    return lab[0] if lab else (t[-1][-40:] if t else "?")

print("%-10s %-8s %-6s %s" % ("local", "numsc", "sep", "undname-scope"))
for s in syms:
    mm = re.search(r"@\?([0-9A-P]+)([?@])", s)
    nm = re.search(r"\?A[VU](L\d+)@", s).group(1)
    print("%-10s %-8s %-6s %s" % (nm, mm.group(1), mm.group(2), und(s)))
