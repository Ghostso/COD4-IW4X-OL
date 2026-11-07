#!/usr/bin/env python3
"""B7: 直接 dump obj 里所有局域类符号."""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WORK = os.path.join(os.environ["TEMP"], "s137_msvc_b7b")
obj = open(os.path.join(WORK, "t.obj"), "rb").read()
pat = re.compile(rb"\?A[VU][A-Za-z0-9_?$<>{},]*@\?[0-9A-P]+[?@]")
seen = set()
for m in pat.finditer(obj):
    s = m.group(0).decode("latin1")
    if s not in seen:
        seen.add(s)
        print(s)
print("total", len(seen))
