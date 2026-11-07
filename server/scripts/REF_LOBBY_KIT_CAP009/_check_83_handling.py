# -*- coding: utf-8 -*-
"""看本轮 8/3 是否被接住、档案是否重建。"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(ROOT, "lobby_srv.log")
PUB = os.path.join(ROOT, "player_profiles", "public.result")
UP = os.path.join(ROOT, "player_profiles", "uploaded_public.bin")


def main():
    lines = open(LOG, "r", encoding="utf-8", errors="replace").read().splitlines()
    hits = [l for l in lines if "profile" in l.lower() or "8/3" in l]
    print("日志里 profile/8-3 相关 %d 行:" % len(hits))
    for l in hits[-20:]:
        print("  %s" % l.strip()[:160])
    print()
    for p in (PUB, UP):
        if os.path.exists(p):
            st = os.stat(p)
            print("%s: %d 字节, 修改时间 %s"
                  % (os.path.basename(p), st.st_size,
                     __import__("time").strftime("%H:%M:%S",
                                                 __import__("time").localtime(st.st_mtime))))
        else:
            print("%s: 不存在" % os.path.basename(p))
    return 0


if __name__ == "__main__":
    sys.exit(main())
