#!/usr/bin/env python3
"""找 call rel32 -> 目标函数的全部调用点, 并回溯每处所在函数与邻近 push 串.
用法: python -I tools/callsite_finder.py 0x4B7C50 [0x9B7B88 refs]
"""
import struct, re, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read(); N = len(d)
def out(s): sys.stdout.write(s.encode("ascii","replace").decode("ascii")+"\n")
def cstr(off, ml=400):
    if not (0 <= off < N): return None
    e = d.find(b"\x00", off);
    if e < 0 or e-off > ml: e = off+ml
    return d[off:e]

targets = [int(a,16) for a in sys.argv[1:]]
md = Cs(CS_ARCH_X86, CS_MODE_32)

for tgt in targets:
    out("="*76)
    out("### 目标 0x%08X (file 0x%06X) 的调用点 + 指针引用" % (tgt, tgt-VA))
    tfile = tgt - VA
    if 0 <= tfile < N:
        s = cstr(tfile, 300)
        if s and len(s)>=2 and all(32<=c<127 for c in s):
            out("    目标处字符串: %r" % s.decode("latin1")[:120])
    calls = []
    for i in range(N-5):
        if d[i] == 0xE8:
            rel = struct.unpack_from("<i", d, i+1)[0]
            if (i + VA + 5 + rel) & 0xFFFFFFFF == tgt & 0xFFFFFFFF:
                calls.append(i)
    out("    call rel32 调用点: %s" % [hex(c) for c in calls])
    ptrs = [m.start() for m in re.finditer(re.escape(struct.pack("<I", tgt)), d)]
    out("    4B 指针立即数/数据引用: %s" % [hex(p) for p in ptrs[:20]])
    # 每处调用点回溯函数入口 + 附近 push 串
    for c in calls:
        lo = max(0, c-0x600)
        fn = None
        for k in range(c, lo, -1):
            if d[k:k+3] == b"\x55\x8b\xec":
                fn = k; break
        out("    --- call@0x%06X  fn=%s ---" % (c, hex(fn) if fn else "?"))
        # 打印 fn..call 之间所有 push imm32 字符串
        start = fn if fn is not None else max(0, c-0x200)
        for h in range(start, c):
            if d[h] == 0x68:
                v = struct.unpack_from("<I", d, h+1)[0]
                if VA <= v < VA+N:
                    t = cstr(v-VA, 200)
                    if t and len(t)>=3 and all(32<=x<127 for x in t):
                        out("         push@0x%06X -> 0x%06X %r" % (h, v-VA, t.decode("latin1")[:110]))
