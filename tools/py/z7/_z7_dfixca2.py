# -*- coding: utf-8 -*-
import os, re, shutil, time
p = r"run_codol_001\sandbox_datafix_20260929\cacert.pem"
ca = r"CODOLServer\lobby3074\codol_ca.pem"
CARAW = open(ca, "rb").read()
raw = open(p, "rb").read()
print("current size:", len(raw))
# already appended? compare tail
if raw.endswith(CARAW):
    print("CA already at tail -> nothing to do")
else:
    bak = p + ".bak_z7ca_" + time.strftime("%Y%m%d_%H%M%S")
    shutil.copy2(p, bak)
    new = raw if raw.endswith(b"\n") else raw + b"\n"
    new = new + CARAW
    open(p, "wb").write(new)
    chk = open(p, "rb").read()
    print("appended: %d -> %d" % (len(raw), len(chk)))
    print("tail match:", chk.endswith(CARAW))
    print("backup:", bak)
