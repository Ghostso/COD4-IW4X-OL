#!/usr/bin/env python3
"""129 卷: 三个入队入口的完整调用点普查 -> 全串 + 时间口径.
输出一张 '入口/函数/事件/完整模板/项数/时间口径' 的表.
"""
import struct, re, sys
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read(); N = len(d)
def out(s): sys.stdout.write(s.encode("ascii","replace").decode("ascii")+"\n")
def cstr(f):
    if not (0 <= f < N): return None
    e = d.find(b"\x00", f)
    if e < 0: e = N
    return d[f:e]

ENTRIES = {0x6404B0: "0x6404B0 登记器(可运行时拼串)",
           0x640190: "0x640190 直接入队(单条模板)",
           0x640FD0: "0x640FD0 log_event(名+值)"}

TS_PH  = "0x9BB744"; IP_PH = "0x9B4CF8"; TS = "0x9B48E4"

def callsites(tgt):
    res = []
    for i in range(N-5):
        if d[i] == 0xE8:
            rel = struct.unpack_from("<i", d, i+1)[0]
            if (i+VA+5+rel) & 0xFFFFFFFF == tgt & 0xFFFFFFFF:
                res.append(i)
    return res

def prologue_before(c, limit=0x800):
    lo = max(0, c-limit)
    for k in range(c, lo, -1):
        if d[k:k+3] == b"\x55\x8b\xec":
            return k
    return None

rows = []
for ent, label in ENTRIES.items():
    out("#"*80)
    out("## %s" % label)
    out("#"*80)
    for c in callsites(ent):
        fn = prologue_before(c)
        start = fn if fn is not None else max(0, c-0x300)
        # 收集 fn..call 之间的 push imm32 -> ascii 串
        strs = []
        for h in range(start, c):
            if d[h] == 0x68:
                v = struct.unpack_from("<I", d, h+1)[0]
                if VA <= v < VA+N:
                    t = cstr(v-VA)
                    if t and len(t) >= 2 and all(32 <= x < 127 for x in t):
                        strs.append((v, t.decode("latin1")))
        # 事件模板 = 含 '|' 且首段匹配事件名 的最长串
        tmps = [(a, s) for a, s in strs if "|" in s and re.match(r"[A-Za-z][A-Za-z0-9_]{2,40}\|", s)]
        tmpl = max(tmps, key=lambda x: len(x[1])) if tmps else None
        ph = []
        if any(a == eval(TS_PH) for a, s in strs): ph.append("TS_PH")
        if any(a == eval(IP_PH) for a, s in strs): ph.append("IP_PH")
        if any(a == eval(TS) for a, s in strs): ph.append("TS(literal)")
        if tmpl:
            s = tmpl[1]
            if "${TIMESTAMP}" in s: ph.append("TS(inline)")
            if "${TIMESTAMP_OFFSET" in s: ph.append("TS_OFFSET(inline)")
            if "${ZONEID" in s: ph.append("ZONEID")
            if "${CODOID(%s)}" in s: ph.append("CODOID(%s)")
            if "${CODOID(%llu)}" in s: ph.append("CODOID(%llu)")
            items = s.count("%") + 1
        else:
            items = 0
        out("")
        out("  call@file0x%06X  fn=0x%06X" % (c, fn if fn else -1))
        if tmpl:
            out("    事件 = %s" % tmpl[1].split("|")[0])
            out("    模板 = %r" % tmpl[1])
            out("    项数=%d  时间口径=%s" % (items, ",".join(ph) or "无"))
        else:
            out("    (无事件模板) 串=%s" % [s for a, s in strs][:8])
        # 追加片段 (以 | 开头, 非模板) —— 运行时拼接证据
        frags = [(a, s) for a, s in strs if s.startswith("|") or s.startswith("%d,")]
        if frags:
            out("    ★追加片段: %s" % [s for a, s in frags])
        rows.append((ent, c, fn, tmpl[1] if tmpl else "", items, ",".join(ph)))

out("")
out("="*80)
out("汇总: 共 %d 个日志点" % len(rows))
out("="*80)
byent = {}
for r in rows: byent.setdefault(r[0], []).append(r)
for ent, label in ENTRIES.items():
    lst = byent.get(ent, [])
    out("%s : %d 点" % (label, len(lst)))
    evs = sorted(set(r[3].split("|")[0] for r in lst if r[3]))
    out("    事件(%d): %s" % (len(evs), ", ".join(evs)))
