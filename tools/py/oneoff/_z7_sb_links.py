# -*- coding: utf-8 -*-
import os
SB = os.path.join("run_codol_001","sandbox_ifs1_20260923")
print("=== sandbox entries that are junctions/symlinks ===")
for n in sorted(os.listdir(SB)):
    p = os.path.join(SB, n)
    if os.path.islink(p) or os.path.isdir(p):
        try:
            tgt = os.path.realpath(p)
        except Exception:
            tgt = "?"
        mark = "LINK" if os.path.islink(p) else "DIR "
        print("  %s %-28s -> %s" % (mark, n, tgt))
