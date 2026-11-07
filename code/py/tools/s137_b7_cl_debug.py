#!/usr/bin/env python3
"""B7 debug: 抓 cl 全输出."""
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WORK = os.path.join(os.environ["TEMP"], "s137_msvc_b7")
os.makedirs(WORK, exist_ok=True)
VCV = r"E:\BuildTools\VC\Auxiliary\Build\vcvars32.bat"
print("WORK=", WORK, "exists", os.path.exists(WORK))
print("VCV exists", os.path.exists(VCV))
cpp = os.path.join(WORK, "t.cpp")
if not os.path.exists(cpp):
    open(cpp, "w").write("struct B{virtual ~B();};void bar(void){struct L1:B{virtual void f();};}\n")
cmd = 'call %s && cd /d %s && cl /c /nologo /EHsc /GR t.cpp' % (VCV, WORK)
r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
print("exit", r.returncode)
print("--- STDOUT ---")
print((r.stdout or "")[-4000:])
print("--- STDERR ---")
print((r.stderr or "")[-4000:])
