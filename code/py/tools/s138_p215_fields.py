#!/usr/bin/env python3
"""s138_p215_fields: 统计 21/5 各槽位取值分布(含 crc32 反解), 区分 35B/75B 两种形态。"""
import json
import sys
import zlib
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, "tools")
import s138_21_resolve as R

CORPUS = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
name_crc = {}
for s in ["combat", "sd", "coop", "playlist", "tdm", "dm", "cha", "war", "dom", "kc", "hp", "ctf",
          "ffa", "gun", "spy", "borg", "zhunt", "dmz", "asym", "sdp", "hostage", "vip", "tjugg"]:
    name_crc[zlib.crc32(s.encode()) & 0xffffffff] = s

corpus = json.load(open(CORPUS, encoding="utf-8"))
by_len = Counter()
slots = {}
for r in corpus:
    if r["svc"] != 21 or r["task"] != 5:
        continue
    b = bytes.fromhex(r["payload"])
    by_len[len(b)] += 1
    els, _ = R.parse(b)
    sig = len(els)
    for i, (t, v) in enumerate(els):
        if t in (0x07, 0x08):
            u = v & 0xffffffff
            slots.setdefault((len(b), i), Counter())[name_crc.get(u, u)] += 1

print("长度分布:", dict(by_len))
for key in sorted(slots):
    ln, i = key
    print("  len=%d #%02d: %s" % (ln, i, dict(slots[key])))
