# -*- coding: utf-8 -*-
"""Remove the CODOL local CA that was added to LocalMachine\\Root."""
import subprocess
import sys

TB = "84CAEFFBB8E63F5146D4DB72849491267772B920"


def run(args):
    r = subprocess.run(args, capture_output=True)
    out = r.stdout.decode("utf-8", "replace")
    err = r.stderr.decode("utf-8", "replace")
    return r.returncode, out, err


def count_in_store(store):
    rc, out, _ = run(["certutil", "-store", store])
    return out.count(TB)


print("thumbprint:", TB)
print("before LocalMachine\\Root :", count_in_store("Root"))

rc, out, err = run(["certutil", "-delstore", "Root", TB])
print("delstore Root rc =", rc)
print("out:", out.strip()[:400])

rc2, out2, err2 = run(["certutil", "-user", "-delstore", "Root", TB])
print("delstore user Root rc =", rc2)
print("out:", out2.strip()[:400])

print("after  LocalMachine\\Root :", count_in_store("Root"))

rc, out, _ = run(["reg", "query",
                  r"HKLM\SOFTWARE\Microsoft\SystemCertificates\Root\Certificates\%s" % TB])
print("registry key present:", rc == 0)

rc, out, _ = run(["reg", "query",
                  r"HKCU\SOFTWARE\Microsoft\SystemCertificates\Root\Certificates\%s" % TB])
print("HKCU registry key present:", rc == 0)
