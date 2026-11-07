# -*- coding: utf-8 -*-
"""看 8/1 8/2 8/3 在会话里的出现时机, 以及 public.result 何时被改。"""
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(ROOT, "lobby_srv.log")
PROF = os.path.join(ROOT, "player_profiles")


def main():
    print("现在: %s" % time.strftime("%H:%M:%S"))
    print()
    lines = open(LOG, "r", encoding="utf-8", errors="replace").read().splitlines()
    for i, l in enumerate(lines):
        m = re.search(r"service=8 ver=\S+ task=(\d+)", l)
        if m:
            note = lines[i + 1].strip() if i + 1 < len(lines) else ""
            print("  %s" % l.strip()[:110])
            if note:
                print("        %s" % note[:110])
    print()
    for fn in sorted(os.listdir(PROF)):
        p = os.path.join(PROF, fn)
        if os.path.isfile(p):
            st = os.stat(p)
            print("  %-28s %8d  %s" % (fn, st.st_size,
                                        time.strftime("%H:%M:%S",
                                                      time.localtime(st.st_mtime))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
