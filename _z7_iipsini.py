# -*- coding: utf-8 -*-
import os, hashlib
cands = [
  r"run_codol_001\sandbox_ifs1_20260923\iips.ini",
  r"run_codol_001\sandbox_ifs1_20260923\IIPS\iips.ini",
  r"COD OL\iips.ini",
  r"COD OL\IIPS\iips.ini",
  r"??\EX035_DIR\iips.ini",
]
for c in cands:
    if os.path.isfile(c):
        b=open(c,"rb").read()
        print("EXISTS  %-58s %3d  %s" % (c, len(b), hashlib.sha256(b).hexdigest()[:16].upper()))
        print("        %r" % b)
    else:
        print("MISSING %s" % c)
