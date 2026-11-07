# -*- coding: utf-8 -*-
import os
SB = os.path.join("run_codol_001","sandbox_ifs1_20260923")
print("=== root FILES in sandbox ===")
for n in sorted(os.listdir(SB)):
    p = os.path.join(SB, n)
    if os.path.isfile(p):
        print("  %-46s %9d  %s" % (n, os.path.getsize(p), __import__("time").strftime("%Y-%m-%d %H:%M", __import__("time").localtime(os.path.getmtime(p)))))
print()
print("=== key files check ===")
for n in ["codoMP_client_shipRetail.exe","codoMP_client_shipRetailBase.dll","iips.ini","dwauth.ini","cacert.pem"]:
    p = os.path.join(SB,n)
    print("  %-40s exists=%s size=%s" % (n, os.path.isfile(p), os.path.getsize(p) if os.path.isfile(p) else "-"))
