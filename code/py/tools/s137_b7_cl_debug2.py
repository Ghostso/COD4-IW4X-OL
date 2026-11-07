#!/usr/bin/env python3
"""B7 debug2: 抓 cl 全输出 (bytes)."""
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WORK = os.path.join(os.environ["TEMP"], "s137_msvc_b7")
VCV = r"E:\BuildTools\VC\Auxiliary\Build\vcvars32.bat"
cmd = 'call %s && cd /d %s && cl /c /nologo /EHsc /GR t.cpp' % (VCV, WORK)
r = subprocess.run(cmd, shell=True, capture_output=True, timeout=300)
print("exit", r.returncode)
print("--- STDOUT ---")
print(r.stdout.decode("latin1", "replace"))
print("--- STDERR ---")
print(r.stderr.decode("latin1", "replace"))
