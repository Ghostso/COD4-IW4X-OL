#!/usr/bin/env python3
"""s138_p21_gtfield: 统计 21/1 #24 与 21/12 #26 的取值, 与 playlist id / 显式 gametype 的关系。"""
import json
import re
import sys
import zlib
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, "tools")
import s138_21_resolve as R

CORPUS = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
P = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\playlist_plain.txt"

lines = open(P, encoding="latin1").read().splitlines()
pl = {}
cur = None
for l in lines:
    m = re.match(r"^\s*playlist\s+(\d+)\s*$", l)
    if m:
        cur = int(m.group(1))
        pl[cur] = {"maps": [], "gts": [], "cat": None}
        continue
    if cur is not None:
        m = re.match(r"^\s*([a-z0-9_]+)\s*,\s*([a-z0-9_]+)\s*,\s*\d+", l)
        if m:
            pl[cur]["maps"].append(m.group(1))
            pl[cur]["gts"].append(m.group(2))
        m = re.match(r"^\s*category\s+(\S+)", l)
        if m:
            pl[cur]["cat"] = m.group(1)

name_crc = {}
for s in ["combat", "sd", "coop", "playlist", "tdm", "dm", "cha", "war", "dom", "kc", "hp", "ctf",
          "ffa", "gun", "spy", "borg", "zhunt", "dmz", "asym", "sdp", "hostage", "vip", "tjugg",
          "zsurv", "zm", "clash", "robbery", "oic", "sr", "tag", "ph", "chicken", "sas", "nftbl",
          "zarena", "zchamp"]:
    name_crc[zlib.crc32(s.encode()) & 0xffffffff] = s


def main():
    corpus = json.load(open(CORPUS, encoding="utf-8"))
    for svc, task, gt_slot, pl_slot in [(21, 1, 24, 20), (21, 12, 26, 22)]:
        print("=== %d/%d  (#%d gt, #%d playlist) ===" % (svc, task, gt_slot, pl_slot))
        pair = Counter()
        examples = defaultdict(list)
        for r in corpus:
            if r["svc"] != svc or r["task"] != task:
                continue
            els, _ = R.parse(bytes.fromhex(r["payload"]))
            vals = {}
            for i, (t, v) in enumerate(els):
                if t in (0x07, 0x08):
                    vals[i] = v & 0xffffffff
            g = vals.get(gt_slot, 0xffffffff)
            p = vals.get(pl_slot, 0xffffffff)
            gname = name_crc.get(g, hex(g))
            cat = pl[p]["cat"] if p in pl else None
            gts = sorted(set(pl[p]["gts"])) if p in pl else []
            pair[(p, cat, tuple(gts), gname)] += 1
            if len(examples[(p, gname)]) < 2:
                examples[(p, gname)].append(r["run"])
        for k, c in sorted(pair.items(), key=lambda x: str(x)):
            p, cat, gts, gname = k
            print("  playlist=%-4s cat=%-4s gts=%-14s #gt=%-9s x%d" % (p, cat, gts, gname, c))
        print()


if __name__ == "__main__":
    main()
