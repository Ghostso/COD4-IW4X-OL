#!/usr/bin/env python3
"""52 条客户端模板 与 语料实测字段数 逐条对账 (精确版).
规则: 实测项数 = 1(事件名) + 模板填充指令数. 模板填充指令数 = body.count('%').
另: 抽出镜像里所有以 '|%' 开头的"续接片段", 解释 ClientLoadout/LoadoutChangeEvent 的字段膨胀.
"""
import json, struct, zlib, re, sys, collections
E = r"E:\codol_re\client_image_20261027.bin"
CORPUS = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
FIXED = {0x01: 1, 0x03: 1, 0x06: 2, 0x07: 4, 0x08: 4, 0x09: 8, 0x0a: 8}

def out(s):
    sys.stdout.write(s.encode("ascii", "replace").decode("ascii") + "\n")

d = open(E, "rb").read()
tmpl = {}
for m in re.finditer(rb"([A-Z][A-Za-z0-9_]{2,40})\|(?=[%$][^|\x00]{0,40}\|)", d):
    name = m.group(1).decode("latin1"); off = m.start()
    if name in tmpl: continue
    e = d.find(b"\x00", off)
    tmpl[name] = d[off:e].decode("latin1")

def blobs(payload):
    res = []; i = 0; n = len(payload)
    while i < n:
        t = payload[i]; i += 1
        if t == 0x00: continue
        if t == 0x10:
            j = payload.find(b"\x00", i)
            if j < 0: break
            i = j + 1; continue
        if t in FIXED:
            i += FIXED[t]; continue
        if t in (0x13, 0x6b, 0x6c):
            if i >= n or payload[i] != 0x08: break
            i += 1
            if i + 4 > n: break
            ln = struct.unpack_from("<I", payload, i)[0]; i += 4
            data = payload[i:i+ln]; i += ln
            if t in (0x6b, 0x6c): i += 4
            if t == 0x13: res.append(data)
            continue
        break
    return res

recs = json.load(open(CORPUS, "r", encoding="utf-8"))
fields = collections.defaultdict(collections.Counter); samples = {}
for r in recs:
    if r.get("svc") != 71: continue
    for b in blobs(bytes.fromhex(r.get("payload", "") or "")):
        if b[:2] in (b"\x78\x01", b"\x78\x9c", b"\x78\xda"):
            try: b = zlib.decompress(b)
            except Exception: pass
        t = b.decode("utf-8", "replace")
        for line in t.replace("\r", "").split("\n"):
            if "|" not in line: continue
            parts = line.split("|"); name = parts[0]
            if not re.match(r"^[A-Z][A-Za-z0-9_]{2,40}$", name): continue
            fields[name][len(parts)] += 1
            samples.setdefault(name, line)

def tmpl_items(t):
    if not t: return None
    return t.count("%") + 1   # 事件名 1 项

out("%-30s %6s %10s  %s" % ("事件名", "模板", "实测", "判定"))
out("-" * 92)
m = mm = ot = oc = 0
for name in sorted(tmpl, key=lambda k: -sum(fields.get(k, {}).values())):
    if name == "LHl": continue
    ti = tmpl_items(tmpl[name])
    if name not in fields:
        ot += 1
        out("%-30s %6d %10s  %s" % (name, ti, "-", "仅模板(语料未触发)"))
        continue
    dist = dict(sorted(fields[name].items()))
    ok = ti in dist
    if ok: m += 1
    else: mm += 1
    out("%-30s %6d %10s  %s" % (name, ti, ",".join(map(str, dist)), "OK" if ok else "DIFF"))
for name in fields:
    if name not in tmpl:
        oc += 1
        out("%-30s %6s %10s  %s" % (name, "-", ",".join(map(str, fields[name])), "仅报文"))
out("-" * 92)
out("命中=%d  DIFF=%d  仅模板=%d  仅报文=%d" % (m, mm, ot, oc))
out("")
out("=== DIFF / 仅报文 样本 ===")
for name in list(fields):
    ti = tmpl_items(tmpl.get(name))
    if ti is None or ti not in fields[name]:
        out("  %-28s 模板(%s项)=%r" % (name, ti, tmpl.get(name)))
        out("  %-28s 实测样本=%r" % ("", samples.get(name, "")[:300]))

out("")
out("=== 镜像中以 '|%' 开头的续接片段 ===")
for mm2 in re.finditer(rb"(?:\x00)(\|%[^|\x00]{1,60}(?:\|[^|\x00]{0,40}){2,})", d):
    off = mm2.start() + 1
    s = mm2.group(1).decode("latin1")
    out("  0x%06X  项数=%d  %r" % (off, s.count("%") + 1, s[:200]))

out("")
out("=== 0x9B7A80..0x9B7C80 串 ===")
i = 0x9B7A80
while i < 0x9B7C80:
    if 32 <= d[i] < 127 and (i == 0 or not (32 <= d[i-1] < 127)):
        e = d.find(b"\x00", i, 0x9B7D00)
        if e < 0: break
        out("  0x%06X  %r" % (i, d[i:e].decode("latin1")))
        i = e + 1
    else:
        i += 1
