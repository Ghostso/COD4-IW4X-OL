# -*- coding: utf-8 -*-
import os, shutil, hashlib, io

def sha(p):
    return hashlib.sha256(open(p,"rb").read()).hexdigest().upper()[:16]

GAME = None
for dp,dn,fn in os.walk("."):
    if "backup" in dp.lower() or "archive" in dp.lower(): continue
    if "COD OL" in dp and "cacert.pem" in fn and "dwauth.ini" in fn:
        GAME = dp; break
print("GAME =", GAME)
print()

pairs = [
 ("dwauth.ini", "dwauth.ini.bak_z7_20261002_2331"),
 ("cacert.pem", "cacert.pem.bak_z7_20261002_2331"),
]
for cur, bak in pairs:
    cp, bp = os.path.join(GAME,cur), os.path.join(GAME,bak)
    print("--- %s ---" % cur)
    print("   current: %9d  %s" % (os.path.getsize(cp), sha(cp)))
    print("   backup : %9d  %s" % (os.path.getsize(bp), sha(bp)))
    shutil.copy2(bp, cp)
    print("   RESTORED -> %9d  %s" % (os.path.getsize(cp), sha(cp)))
    print("   content : %r" % open(cp,"rb").read()[:120])
