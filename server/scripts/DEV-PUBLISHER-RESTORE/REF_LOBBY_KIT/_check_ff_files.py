# -*- coding: utf-8 -*-
"""检查游戏目录 main/*.ff 和磁盘 mp/marketplace.json。"""
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.abspath(os.path.join(ROOT, "..", "run_codol_001",
                                    "sandbox_datafix_20260929"))
MAN = os.path.join(ROOT, "mkt_assets", "marketplace.client.json")


def main():
    j = json.load(open(MAN, "r", encoding="utf-8"))
    want = {}
    for k, v in j.items():
        if isinstance(v, str) and len(v) == 32:
            want[v.upper()] = k
    print("target tables: %d" % len(want))
    mpj = os.path.join(GAME, "mp", "marketplace.json")
    if os.path.exists(mpj):
        raw = open(mpj, "rb").read()
        print("disk mp/marketplace.json: %d bytes" % len(raw))
        print("  %r" % raw[:400])
    mdir = os.path.join(GAME, "main")
    ff = [n for n in sorted(os.listdir(mdir)) if n.endswith(".ff")]
    print("main/*.ff count: %d" % len(ff))
    for n in ff:
        p = os.path.join(mdir, n)
        b = open(p, "rb").read()
        md5 = hashlib.md5(b).hexdigest().upper()
        hit = want.get(md5)
        tag = (" MATCH=" + hit) if hit else ""
        names = list(set(re.findall(rb"[a-zA-Z0-9_/\.\-]{4,60}\.csv", b)))
        print("  %-44s %9d md5=%s%s" % (n, len(b), md5[:12], tag))
        if names:
            print("      csv=%s" % [x.decode("latin1") for x in names[:8]])
        for nd in (b"coMarketplace", b"unlockFlags"):
            if nd in b:
                print("      HAS %s" % nd.decode())
    return 0


if __name__ == "__main__":
    sys.exit(main())
