# -*- coding: utf-8 -*-
import os, shutil, hashlib
GP = os.path.join("COD OL","cacert.pem")
CA = os.path.join("CODOLServer","lobby_server","lobby_ca.pem")
bak = GP + ".bak_z7_20261002_2331"
if not os.path.isfile(bak):
    shutil.copy2(GP, bak)
print("BACKUP ->", bak, os.path.getsize(bak))
print("before size:", os.path.getsize(GP))
print("CA file size:", os.path.getsize(CA))
print("CA sha256:", hashlib.sha256(open(CA,"rb").read()).hexdigest()[:24])
