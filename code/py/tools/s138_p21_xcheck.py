#!/usr/bin/env python3
"""s138_p21_xcheck: 对 21/1 与 21/12 精确交叉核对:
  #19 / #21 = playlist version (796)
  #20 / #22 = playlist ID
  #18 / #20(12) = map 名 crc32
  #24 / #26 = gametype 名 crc32
并验证 playlist ID 的 maps/gametypes 是否**包含**该 map/gametype。
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

crc2map = {}
crc2gt = {}
for pid, d in pl.items():
    for mp in d["maps"]:
        crc2map.setdefault(zlib.crc32(mp.encode()) & 0xffffffff, set()).add(mp)
for pid, d in pl.items():
    for gt in d["gts"]:
        crc2gt.setdefault(zlib.crc32(gt.encode()) & 0xffffffff, set()).add(gt)


def label(u):
    if u in crc2map:
        return "map:" + "/".join(sorted(crc2map[u])[:2])
    if u in crc2gt:
        return "gt:" + "/".join(sorted(crc2gt[u])[:2])
    return None


def main():
    corpus = json.load(open(CORPUS, encoding="utf-8"))
    for svc, task, slots in [(21, 1, {"ver": 19, "playlist": 20, "map": 18, "gt": 24}),
                             (21, 12, {"ver": 21, "playlist": 22, "map": 20, "gt": 26}),
                             (21, 5, {"playlist": 2})]:
        print("=== %d/%d ===" % (svc, task))
        n = 0
        for r in corpus:
            if r["svc"] != svc or r["task"] != task:
                continue
            els, _ = R.parse(bytes.fromhex(r["payload"]))
            vals = {}
            for i, (t, v) in enumerate(els):
                if t in (0x07, 0x08):
                    vals[i] = v & 0xffffffff
            plid = vals.get(slots["playlist"])
            mt = vals.get(slots.get("map", -1), 0xffffffff)
            gt = vals.get(slots.get("gt", -1), 0xffffffff)
            ver = vals.get(slots.get("ver", -1))
            mapname = "/".join(sorted(crc2map[mt])) if mt in crc2map else None
            gtname = "/".join(sorted(crc2gt[gt])) if gt in crc2gt else None
            inpl = ""
            if plid in pl and mapname and gtname:
                mm = mapname.split("/")[0]
                gg = gtname.split("/")[0]
                inpl = " mapInPlaylist=%s gtInPlaylist=%s" % (
                    mm in pl[plid]["maps"], gg in pl[plid]["gts"])
            print("  run=%s playlist=%s ver=%s map=%s gt=%s%s" %
                  (r["run"], plid, ver, mapname, gtname, inpl))
            n += 1
            if n >= 12:
                break
        print()


if __name__ == "__main__":
    main()
