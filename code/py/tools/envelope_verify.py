#!/usr/bin/env python3
"""语料侧验证"7 字段信封" %s|${TIMESTAMP_PLACEHOLDER}|%u|%llu|%s|${CODOID(%s)}|%s
(= 事件名|时间偏移|%u|%llu|%s|CODOID|%s).
做法: 解出 71/3 与 71/15 的遥测文本行, 按 | 切, 统计每个事件名的字段总数分布.
"""
import json, struct, zlib, re, sys, collections

CORPUS = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
FIXED = {0x01: 1, 0x03: 1, 0x06: 2, 0x07: 4, 0x08: 4, 0x09: 8, 0x0a: 8}

def out(s):
    sys.stdout.write(s.encode("ascii", "replace").decode("ascii") + "\n")

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
if isinstance(recs, dict):
    recs = recs.get("records") or recs.get("data") or list(recs.values())

def texts(rec):
    out_s = []
    for b in blobs(bytes.fromhex(rec.get("payload","") or "")):
        # 71/15 是 zlib
        if b[:2] == b"\x78\x01" or b[:2] == b"\x78\x9c" or b[:2] == b"\x78\xda":
            try: b = zlib.decompress(b)
            except Exception: pass
        try:
            t = b.decode("utf-8", "replace")
        except Exception:
            continue
        if "\n" in t or "|" in t:
            out_s.append(t)
    return out_s

fields = collections.defaultdict(collections.Counter)
samples = {}
ntask = collections.Counter()
for r in recs:
    svc = r.get("svc"); tk = r.get("task")
    if svc != 71: continue
    ntask[tk] += 1
    for t in texts(r):
        for line in t.replace("\r", "").split("\n"):
            if "|" not in line: continue
            parts = line.split("|")
            name = parts[0]
            if not re.match(r"^[A-Z][A-Za-z0-9_]{2,40}$", name): continue
            fields[name][len(parts)] += 1
            samples.setdefault(name, line)

out("=== 71/* task 分布 ===")
out("  " + ", ".join("%d:%d" % kv for kv in sorted(ntask.items())))
out("")
out("=== 事件名 -> 字段总数分布 (计数) ===")
for name in sorted(fields, key=lambda k: -sum(fields[k].values())):
    c = fields[name]
    out("  %-30s %s   sample=%r" % (name, dict(c), samples[name][:120]))

