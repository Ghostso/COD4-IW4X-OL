# -*- coding: utf-8 -*-
import os, shutil, sys
ROOT = os.getcwd()
target = None
for dp, dn, fn in os.walk(ROOT):
    if "backup" in dp.lower() or "backups" in dp.lower() or "archive" in dp.lower():
        continue
    if "COD OL" in dp and "dwauth.ini" in fn:
        target = os.path.join(dp, "dwauth.ini")
print("ROOT =", ROOT)
print("TARGET =", target)
if not target:
    sys.exit(1)
print("OLD bytes:", os.path.getsize(target))
with open(target, "rb") as f:
    print("OLD:", repr(f.read()))
bak = target + ".bak_z7_20261002_2331"
shutil.copy2(target, bak)
print("BACKUP ->", bak)
new = ("formal-zone-lsg.codol.qq.com 3074\r\n"
       "formal-zone-auth.codol.qq.com 3074\r\n"
       "0x03EA\r\n")
with open(target, "wb") as f:
    f.write(new.encode("ascii"))
print("NEW bytes:", os.path.getsize(target))
with open(target, "rb") as f:
    print("READBACK:", repr(f.read()))
