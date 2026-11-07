# -*- coding: utf-8 -*-
import os
GAME = None
for dp,dn,fn in os.walk("."):
    if "backup" in dp.lower() or "archive" in dp.lower(): continue
    if "COD OL" in dp and "cacert.pem" in fn:
        GAME = dp; break
print("GAME DIR =", GAME)
p = os.path.join(GAME, "cacert.pem")
data = open(p, "rb").read()
print("cacert.pem size:", len(data))
n = data.count(b"-----BEGIN CERTIFICATE-----")
print("cert count:", n)
txt = data.decode("utf-8","replace")
# look for our CA by substring markers
for marker in ["CODOL-LOCAL", "CODOL Local Lobby CA"]:
    print("contains %r:" % marker, marker in txt)
# extract all and check our CA subject
import re
try:
    from cryptography import x509
    blocks = re.findall(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", txt, re.S)
    print("parsed blocks:", len(blocks))
    hits = 0
    for i,b in enumerate(blocks):
        try:
            c = x509.load_pem_x509_certificate(b.encode())
            s = c.subject.rfc4514_string()
            if "CODOL" in s:
                hits += 1
                print("  HIT #%d: %s" % (i, s))
                try:
                    bc = c.extensions.get_extension_for_class(x509.BasicConstraints).value
                    print("        ca=%s pathlen=%s" % (bc.ca, bc.path_length))
                except Exception as e:
                    print("        bc: none")
        except Exception:
            pass
    print("CODOL CA hits in cacert.pem:", hits)
except Exception as e:
    print("cryptography err:", e)
