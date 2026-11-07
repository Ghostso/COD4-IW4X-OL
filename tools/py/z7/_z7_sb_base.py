# -*- coding: utf-8 -*-
import os, hashlib, time
SB = os.path.join("run_codol_001","sandbox_ifs1_20260923")
files = ["iips.ini","dwauth.ini","cacert.pem","codoMP_client_shipRetail.exe",
         "codoMP_client_shipRetailBase.dll",
         os.path.join("IIPS","iips.dll"), os.path.join("IIPS","IFS2.dll"),
         os.path.join("IIPS","HostPid")]
print("=== SANDBOX BASELINE ===")
for f in files:
    p = os.path.join(SB,f)
    if os.path.isfile(p):
        h = hashlib.sha256(open(p,"rb").read()).hexdigest().upper()
        print("  %-42s %9d  %s" % (f, os.path.getsize(p), h[:16]))
    else:
        print("  %-42s <MISSING>" % f)
print()
print("=== iips.ini content ===")
print(repr(open(os.path.join(SB,"iips.ini"),"rb").read()))
print("=== dwauth.ini content ===")
print(repr(open(os.path.join(SB,"dwauth.ini"),"rb").read()))
