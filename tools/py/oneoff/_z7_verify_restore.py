# -*- coding: utf-8 -*-
"""Verify every item this session touched is back to its pre-session value."""
import hashlib
import io
import os
import subprocess


def sha16(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest().upper()[:16]


GAME = os.path.join(os.getcwd(), "COD OL")
SB = os.path.join(os.getcwd(), "run_codol_001", "sandbox_ifs1_20260923")
OK = True


def check(label, got, want, extra=""):
    global OK
    good = got == want
    OK = OK and good
    print("  [%s] %-42s got=%s want=%s %s"
          % ("OK " if good else "BAD", label, got, want, extra))


print("=== 1. COD OL\\dwauth.ini ===")
p = os.path.join(GAME, "dwauth.ini")
check("size", os.path.getsize(p), 39)
check("sha16", sha16(p), "7FC20C0868FD15D4")
print("      content:", repr(open(p, "rb").read()))

print("=== 2. COD OL\\cacert.pem ===")
p = os.path.join(GAME, "cacert.pem")
check("size", os.path.getsize(p), 291449)
check("sha16", sha16(p), "E11735CE43DEB1D2")

print("=== 3. hosts ===")
H = os.path.join(os.environ["windir"], "System32", "drivers", "etc", "hosts")
check("size", os.path.getsize(H), 915)
live = [l for l in io.open(H, encoding="utf-8", errors="replace").read().splitlines()
        if l.strip() and not l.strip().startswith("#")]
check("non-comment lines", len(live), 0)

print("=== 4. CODOL CA in machine Root ===")
TB = "84CAEFFBB8E63F5146D4DB72849491267772B920"
r = subprocess.run(["certutil", "-store", "Root"], capture_output=True)
check("thumbprint present", TB in r.stdout.decode("utf-8", "replace"), False)
r = subprocess.run(
    ["reg", "query",
     r"HKLM\SOFTWARE\Microsoft\SystemCertificates\Root\Certificates\%s" % TB],
    capture_output=True)
check("HKLM regkey exists", r.returncode == 0, False)

print("=== 5. portproxy (never touched) ===")
r = subprocess.run(["netsh", "interface", "portproxy", "show", "v4tov4"],
                   capture_output=True)
txt = r.stdout.decode("gbk", "replace")
check("443->8443 rule present", "8443" in txt, True)
check("443->8444 rule present", "8444" in txt, True)

print("=== 6. sandbox untouched ===")
check("iips.ini sha16", sha16(os.path.join(SB, "iips.ini")), "14DEFEE97155DCF2")
check("iips.dll sha16",
      sha16(os.path.join(SB, "IIPS", "iips.dll")), "E2367C487FF545B4")
check("exe sha16",
      sha16(os.path.join(SB, "codoMP_client_shipRetail.exe")), "36997674B18F2896")
check("dwauth.ini sha16", sha16(os.path.join(SB, "dwauth.ini")), "03B7350AD39BE44F")

print()
print("RESULT:", "ALL RESTORED" if OK else "*** MISMATCH PRESENT ***")
