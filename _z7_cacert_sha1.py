# -*- coding: utf-8 -*-
"""Replace the old CODOL CA inside cacert.pem with the new SHA-1 one."""
import re, shutil, time
from cryptography import x509
NEW = open(r"D:\z7tmp\cert_sha1\ca.pem","rb").read().strip()

TARGETS = [r"COD OL\cacert.pem",
           r"run_codol_001\sandbox_ifs1_20260923\cacert.pem",
           r"run_codol_001\sandbox_datafix_20260929\cacert.pem"]

PEM = re.compile(rb"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", re.S)
for p in TARGETS:
    raw = open(p,"rb").read()
    out = []
    removed = 0
    for b in PEM.findall(raw):
        try:
            c = x509.load_pem_x509_certificate(b + b"\n")
            if "CODOL-LOCAL" in c.subject.rfc4514_string():
                removed += 1
                continue
        except Exception:
            pass
        out.append(b)
    new = b"\n".join(out) + b"\n" + NEW + b"\n"
    bak = p + ".bak_sha1_" + time.strftime("%Y%m%d_%H%M%S")
    shutil.copy2(p, bak)
    open(p,"wb").write(new)
    # verify
    chk = open(p,"rb").read()
    found = 0
    for b in PEM.findall(chk):
        try:
            c = x509.load_pem_x509_certificate(b + b"\n")
            if "CODOL-LOCAL" in c.subject.rfc4514_string():
                found += 1
                subj = c.subject.rfc4514_string()
                sig = c.signature_algorithm_oid._name
        except Exception:
            pass
    print("  %s" % p)
    print("     removed old CODOL certs: %d   now present: %d  (%s, %s)"
          % (removed, found, subj if found else "-", sig if found else "-"))
    print("     size %d -> %d   backup %s" % (len(raw), len(chk), bak))
