"""Why did the last rounds die at 11-15 s with ACE=0/3?

Check the sandbox's boot prerequisites and compare the sandbox used by the
49.7 s run against the one used by the failures.
"""
import glob
import os
import re

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
SAND = os.path.join(ROOT, r"run_codol_001\sandbox_datafix_20260929")

print("=== sandbox prerequisites ===")
for rel in ["TCLS", r"TCLS\TenProtect", r"TCLS\Tenio", "TGuard", "IIPS"]:
    p = os.path.join(SAND, rel)
    if os.path.isdir(p):
        print("  %-22s OK (%d entries)" % (rel, len(os.listdir(p))))
    else:
        print("  %-22s *** MISSING ***" % rel)

print()
print("=== ACE modules present? ===")
for f in ["ace-ats32.dll", "tersafe.dll", "policyprobe.dll",
          "TenRpcs.dll", "TenProxy.dll", "VSDDrvDll.dll", "ACE-DRV32.dll"]:
    p = os.path.join(SAND, f)
    print("  %-20s %s" % (f, os.path.getsize(p) if os.path.exists(p)
                          else "*** missing ***"))

print()
print("=== sandbox used by recent runs ===")
ds = sorted(glob.glob(os.path.join(ROOT, r"run_codol_001\runs\IFS1_*")),
            key=os.path.getmtime)[-8:]
for d in ds:
    lp = os.path.join(d, "launch.txt")
    sb = "-"
    if os.path.exists(lp):
        t = open(lp, encoding="utf-8", errors="replace").read()
        m = re.search(r'--sandbox "([^"]+)"', t)
        sb = os.path.basename(m.group(1)) if m else "-"
    f = os.path.join(d, "aboprobe.stdout")
    life = "-"
    ace = "-"
    if os.path.exists(f):
        x = open(f, "rb").read().decode("gbk", "replace")
        m = re.search(r"lifetime=([\d.]+)", x)
        life = m.group(1) if m else "-"
        ace = sum(1 for k in ["ace-ats32", "tersafe", "policyprobe"] if k in x)
    print("  %-40s life=%-7s ACE=%s  sandbox=%s"
          % (os.path.basename(d)[:40], life, ace, sb))
