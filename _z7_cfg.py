# -*- coding: utf-8 -*-
"""Write the 3-line domain-format dwauth.ini per the working doc section 2.
CRLF line endings, backup + readback verify."""
import os, shutil, time

TARGETS = [
    r"run_codol_001\sandbox_ifs1_20260923\dwauth.ini",
    r"COD OL\dwauth.ini",
]
CONTENT = ("formal-zone-lsg.codol.qq.com 3074\r\n"
           "formal-zone-auth.codol.qq.com 3074\r\n"
           "0x03EA\r\n")

for t in TARGETS:
    if not os.path.isfile(t):
        print("  SKIP (missing): %s" % t); continue
    bak = t + ".bak_z7cfg_" + time.strftime("%Y%m%d_%H%M%S")
    shutil.copy2(t, bak)
    before = open(t, "rb").read()
    with open(t, "wb") as f:
        f.write(CONTENT.encode("ascii"))
    after = open(t, "rb").read()
    print("  %s" % t)
    print("    before: %r" % before)
    print("    after : %r" % after)
    print("    match : %s" % (after == CONTENT.encode("ascii")))
    print("    backup: %s" % bak)
    print()
