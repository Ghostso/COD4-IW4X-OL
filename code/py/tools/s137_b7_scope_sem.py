#!/usr/bin/env python3
"""B7: 局域类序号语义 (重跑, 用已验证的工作目录)."""
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WORK = os.path.join(os.environ["TEMP"], "s137_msvc_b7")
VCV = r"E:\BuildTools\VC\Auxiliary\Build\vcvars32.bat"
os.makedirs(WORK, exist_ok=True)

src = (
    "struct Base{virtual ~Base(){}virtual void f(){}};\n"
    "struct C{void m();};\n"
    "void free1(){\n"
    "  struct A1:Base{virtual void f(){}}; A1 a1; struct A2:Base{virtual void f(){}}; A2 a2;\n"
    "  {struct B1:Base{virtual void f(){}}; B1 b1;}\n"
    "  {struct B2:Base{virtual void f(){}}; B2 b2;}\n"
    "  { {struct D1:Base{virtual void f(){}}; D1 d1;} }\n"
    "}\n"
    "void C::m(){ struct M1:Base{virtual void f(){}}; M1 m1; {struct M2:Base{virtual void f(){}}; M2 m2;} }\n"
    "void free2(){ struct Z1:Base{virtual void f(){}}; Z1 z1; }\n"
)
open(os.path.join(WORK, "t2.cpp"), "w").write(src)

cmd = 'call %s >nul && cd /d %s && cl /c /nologo /EHsc /GR t2.cpp' % (VCV, WORK)
r = subprocess.run(cmd, shell=True, capture_output=True, timeout=300)
print("cl exit", r.returncode)
print(r.stdout.decode("latin1", "replace")[-500:])

objp = os.path.join(WORK, "t2.obj")
print("obj exists", os.path.exists(objp))
if os.path.exists(objp):
    obj = open(objp, "rb").read()
    pat = re.compile(rb"\?A[VU][A-Za-z0-9_]+@\?[0-9A-P]+[?@]\?(free1|free2|m)@")
    seen = sorted(set((m.group(1).decode(), m.group(0).decode()) for m in re.finditer(pat, obj)))
    for fn, s in seen:
        print("  host=%-6s %s" % (fn, s))
    if not seen:
        allm = sorted(set(re.findall(rb"\?A[VU][A-Za-z0-9_]+@\?[0-9A-P]+[?@]", obj)))
        print("  fallback matches:", [x.decode() for x in allm])
