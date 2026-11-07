# -*- coding: utf-8 -*-
import os, hashlib
items = [
 ("AboProbe.exe", r"restore_iips_contract_001\observer2\out\AboProbe.exe"),
 ("tenproxy_shm", r"CODOLServer\_subagents\_tenproxy_shm_fixed.bin"),
 ("sandbox exe", r"run_codol_001\sandbox_ifs1_20260923\codoMP_client_shipRetail.exe"),
 ("observer ps1", r"run_codol_001\elevated_ifs1_observer.ps1"),
 ("chain ps1", r"run_codol_001\capture_elevated_network.ps1"),
]
for name, rel in items:
    if os.path.isfile(rel):
        b = open(rel,"rb").read()
        print("  %-14s OK   %9d  %s  %s" % (name, len(b), hashlib.sha256(b).hexdigest()[:16].upper(),
              __import__("time").strftime("%Y-%m-%d %H:%M", __import__("time").localtime(os.path.getmtime(rel)))))
    else:
        print("  %-14s MISSING  %s" % (name, rel))
