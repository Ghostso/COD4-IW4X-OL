#!/usr/bin/env python3
"""129 卷: 8 条孤儿模板 (有模板串、不在 65 个日志点里) 的引用点与所在函数上下文."""
import struct, re, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read(); N = len(d)
def out(s): sys.stdout.write(s.encode("ascii","replace").decode("ascii")+"\n")
def cstr(f):
    e = d.find(b"\x00", f); return d[f:e]
md = Cs(CS_ARCH_X86, CS_MODE_32)

ORPHANS = ["ClientException","ClientOfflineOOB","ComError","GameMomentsEdit",
           "QuestionnaireResult","UIClickCount","UserComplaint","ClientOfflineOOB"]
OFFS = [0x9DBA48, 0x9E1430, 0x9DB670, 0x9D9768, 0x9D5458, 0x9B8C78, 0x9C2458]

for off in OFFS:
    s = cstr(off)
    name = s.split(b"|")[0].decode("latin1")
    ptr = off + VA
    refs = [m.start() for m in re.finditer(re.escape(struct.pack("<I", ptr)), d)]
    out("="*74)
    out("## %s  @0x%06X  模板=%r" % (name, off, s.decode("latin1")[:130]))
    out("   refs=%s" % [hex(r) for r in refs])
    # 找它的"续接片段"(紧随其后以 | 开头的串)
    nx = off + len(s) + 1
    parts = []
    while nx < N:
        e = d.find(b"\x00", nx)
        t = d[nx:e] if e > nx else b""
        if t and t[:1] in (b"|", b"%") and all(32 <= c < 127 for c in t):
            parts.append(t.decode("latin1")); nx = e+1
        else: break
    if parts: out("   紧随的续接片段: %s" % parts)
    for r in refs:
        lo = max(0, r-0x1000)
        fn = None
        for k in range(r, lo, -1):
            if d[k:k+3] == b"\x55\x8b\xec": fn = k; break
        out("   ref@0x%06X fn=%s" % (r, hex(fn) if fn else "?"))
        # 打印该函数内所有 push 串
        if fn is not None:
            for h in range(fn, min(r+0x40, N)):
                if d[h] == 0x68:
                    v = struct.unpack_from("<I", d, h+1)[0]
                    if VA <= v < VA+N:
                        t = cstr(v-VA)
                        if t and len(t) >= 3 and all(32 <= x < 127 for x in t):
                            out("       push@0x%06X -> %r" % (h, t.decode("latin1")[:100]))
