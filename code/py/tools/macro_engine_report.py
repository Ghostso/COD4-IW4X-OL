#!/usr/bin/env python3
"""宏引擎最终报告 (一次性, 结论汇总, 避免海量输出)."""
import struct, re, sys, collections
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read(); N = len(d)

def out(s):
    sys.stdout.write(s.encode("ascii", "replace").decode("ascii") + "\n")

def cstr(off, ml=300):
    if not (0 <= off < N): return None
    e = d.find(b"\x00", off)
    if e < 0 or e - off > ml: e = off + ml
    return d[off:e]

def refs(v_or_off, is_off=True):
    ptr = (v_or_off + VA) if is_off else v_or_off
    return [m.start() for m in re.finditer(re.escape(struct.pack("<I", ptr)), d)]

out("=== 1) %% 信封前缀串 '%s|${TIMESTAMP_PLACEHOLDER}' @0x192ada 引用点 ===")
out("  refs: %s" % [hex(h) for h in refs(0x192ada)])
out("  该串 = %r" % cstr(0x192ada))

out("")
out("=== 2) 全镜像 '%s%d|' 形态串 @0x9E1450 引用点 ===")
out("  refs: %s" % [hex(h) for h in refs(0x9E1450)])

out("")
out("=== 3) 所有宏/占位符串 + 引用数 ===")
seen = {}
for m in re.finditer(rb"\$\{[A-Z_]+(?:\((?:%[a-z]+|\d+)\))?\}", d):
    off = m.start()
    if off in seen: continue
    e = d.find(b"\x00", off)
    if e < 0: continue
    s = d[off:e].decode("latin1")
    # 必须是"独占串"(前面是 NUL)
    if off and d[off-1] != 0: continue
    r = refs(off)
    seen[s] = (off, r)
for s, (off, r) in sorted(seen.items(), key=lambda kv: kv[1][0]):
    out("  %-34s 0x%06X refs=%2d  %s" % (s[:34], off, len(r), [hex(h) for h in r[:6]]))

out("")
out("=== 4) 0x240CB0 (另一函数, 入口) 附近的串引用 ===")
for h in range(0x240CB0, 0x241000):
    if d[h] == 0x68:
        v = struct.unpack_from("<I", d, h + 1)[0]
        if VA <= v < VA + N:
            t = cstr(v - VA, 100)
            if t and all(32 <= c < 127 for c in t) and len(t) >= 3:
                out("  push@0x%06X  -> 0x%06X %r" % (h, v - VA, t.decode("latin1")[:100]))
