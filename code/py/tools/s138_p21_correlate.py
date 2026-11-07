#!/usr/bin/env python3
"""s138_p21_correlate: 对 21/1、21/12、21/5 的数值字段做 crc32 反解并交叉核对
(playlist id / playlist version / map crc32 / gametype crc32)。
"""
import json
import re
import sys
import zlib

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, "tools")
import s138_21_resolve as R

CORPUS = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
P = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\playlist_plain.txt"

# 构建 playlist 表: id -> {maps:[...], gametypes:[...], version, vsrule, cat}
lines = open(P, encoding="latin1").read().splitlines()
pl = {}
cur = None
ver = None
for l in lines:
    m = re.match(r"^\s*version\s+(\d+)", l)
    if m:
        ver = int(m.group(1))
    m = re.match(r"^\s*playlist\s+(\d+)\s*$", l)
    if m:
        cur = int(m.group(1))
        pl[cur] = {"maps": [], "gts": [], "version": ver, "cat": None, "vsrule": None}
        continue
    if cur is not None:
        m = re.match(r"^\s*([a-z0-9_]+)\s*,\s*([a-z0-9_]+)\s*,\s*\d+", l)
        if m:
            pl[cur]["maps"].append(m.group(1))
            pl[cur]["gts"].append(m.group(2))
        m = re.match(r"^\s*category\s+(\S+)", l)
        if m:
            pl[cur]["cat"] = m.group(1)
        m = re.match(r'^\s*vsrule\s+"?([0-9Vv]+)"?', l)
        if m:
            pl[cur]["vsrule"] = m.group(1)

# 反向: crc32 -> 名称
crc_map = {}
for pid, d in pl.items():
    for mp in d["maps"]:
        crc_map.setdefault(zlib.crc32(mp.encode()) & 0xffffffff, set()).add(mp)
for gt in ["combat", "sd", "coop", "playlist", "tdm", "dm", "cha", "war", "dom", "kc", "hp", "ctf", "ffa",
           "gun", "spy", "borg", "zhunt", "dmz", "asym", "sdp", "hostage", "vip", "tjugg", "zsurv", "zm",
           "clash", "robbery", "oic", "sr", "tag", "ph", "chicken", "sas", "nftbl", "zarena", "zchamp"]:
    crc_map.setdefault(zlib.crc32(gt.encode()) & 0xffffffff, set()).add(gt)


def name_of(u):
    s = crc_map.get(u)
    return "/".join(sorted(s)[:3]) if s else None


def main():
    corpus = json.load(open(CORPUS, encoding="utf-8"))
    for svc, task, idxs in [(21, 1, [18, 19, 20, 24]), (21, 12, [20, 21, 22, 26]), (21, 5, [2, 5, 6, 8, 9, 10])]:
        print("=== %d/%d ===" % (svc, task))
        shown = 0
        for r in corpus:
            if r["svc"] != svc or r["task"] != task:
                continue
            els, _ = R.parse(bytes.fromhex(r["payload"]))
            vals = {}
            for i, (t, v) in enumerate(els):
                if t in (0x07, 0x08):
                    vals[i] = v & 0xffffffff
            # find playlist id candidate
            plid = None
            for cand in vals.values():
                if cand in pl:
                    plid = cand
                    break
            desc = " ".join("#%d=%s" % (i, name_of(vals[i]) or vals[i]) for i in idxs if i in vals)
            if plid is not None:
                d = pl[plid]
                desc += "   | playlist %d: map0=%s gt0=%s ver=%s cat=%s" % (
                    plid, d["maps"][0] if d["maps"] else "?", d["gts"][0] if d["gts"] else "?",
                    d["version"], d["cat"])
            print("  run=%s %s" % (r["run"], desc))
            shown += 1
            if shown >= 6:
                break
        print()


if __name__ == "__main__":
    main()
