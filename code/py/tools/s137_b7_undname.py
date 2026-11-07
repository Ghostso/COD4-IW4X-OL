#!/usr/bin/env python3
"""B7: 用 undname.exe 反解全部局域类 mangled 名 (纯静态 demangle)."""
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
UND = r"E:\BuildTools\VC\Tools\MSVC\14.44.35207\bin\Hostx86\x86\undname.exe"
VA = 0x400000
d = open(E, "rb").read()

HEAD = re.compile(rb"\.\?A[VU][A-Za-z0-9_]+_SF_Handler@|\?AVMyEventHandler@|\?AVCAntiClientSinkImpl@")


def cstr(f, maxlen=400):
    e = d.find(b"\x00", f)
    if e < 0 or e - f > maxlen:
        return None
    return d[f:e].decode("latin1")


strings = []
seen = set()
for m in re.finditer(rb"\?\?|\?AVMyEventHandler@|\?AVCAntiClientSinkImpl@", d):
    pass

# simpler: 收集所有 cstr 起点以 .?AU..._SF_Handler@ 或 .?AVMy/CAnti
for m in re.finditer(rb"\.\?AU[A-Za-z0-9_]+_SF_Handler@|\?\?AVMyEventHandler@|\?\?AVCAntiClientSinkImpl@", d):
    pass

pats = [rb"\.\?AU[A-Za-z0-9_]+_SF_Handler@", rb"\.\?A[VU][A-Za-z0-9_]+@\?[0-9A-P]+[?@]"]
hits = {}
for pat in pats:
    for m in re.finditer(pat, d):
        f = m.start()
        s = cstr(f)
        if s and s not in seen:
            seen.add(s)
            hits[s] = f

print("待反解 %d 条" % len(hits))
print()
for s in sorted(hits, key=lambda x: hits[x]):
    try:
        r = subprocess.run([UND, s], capture_output=True, text=True, timeout=20)
        out = (r.stdout or "").strip() + " " + (r.stderr or "").strip()
    except Exception as ex:
        out = "ERR %s" % ex
    print("IN : %s" % s)
    print("OUT: %s" % out.replace("\r\n", " | ").strip())
    print()
