# -*- coding: utf-8 -*-
import os
K = r"DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT"
for name in ("lobby_srv.log",):
    p = os.path.join(K, name)
    lines = open(p, encoding="utf-8", errors="replace").read().splitlines()
    print("=== %s (%d lines) ===" % (name, len(lines)))
    for i, l in enumerate(lines):
        if "recv" in l and ("10054" in l or "Reset" in l or "\u5f02\u5e38" in l):
            print("--- RST at line %d ---" % i)
            for j in range(max(0, i - 12), min(len(lines), i + 6)):
                mark = ">>" if j == i else "  "
                print("%s %4d %s" % (mark, j, lines[j][:120]))
            print()
