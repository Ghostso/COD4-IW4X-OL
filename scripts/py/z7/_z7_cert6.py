# -*- coding: utf-8 -*-
import os, re, hashlib, warnings
warnings.filterwarnings("ignore")
from cryptography import x509
from cryptography.hazmat.primitives.serialization import Encoding

def fp(c):
    return hashlib.sha256(c.public_bytes(Encoding.DER)).hexdigest()

GR = os.path.join("CODOLServer","lobby_server")
ca   = x509.load_pem_x509_certificate(open(os.path.join(GR,"lobby_ca.pem"),"rb").read())
leaf = x509.load_pem_x509_certificate(open(os.path.join(GR,"lobby_server.pem"),"rb").read())
print("lobby_ca.pem   fp:", fp(ca))
print("leaf issuer    :", leaf.issuer.rfc4514_string())
print("leaf.issuer==ca.subject:", leaf.issuer.public_bytes()==ca.subject.public_bytes())

print("\n--- game cacert.pem ---")
p = os.path.join("COD OL","cacert.pem")
txt = open(p,"rb").read().decode("utf-8","replace")
blocks = re.findall(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", txt, re.S)
print("blocks:", len(blocks))
found = []
for i,b in enumerate(blocks):
    try:
        c = x509.load_pem_x509_certificate(b.encode())
        s = c.subject.rfc4514_string()
        if "CODOL" in s:
            found.append((i, fp(c), s))
    except Exception:
        pass
for i,f,s in found:
    print("  idx=%d  %s" % (i,s))
    print("        fp=%s" % f)
    print("        == lobby_ca.pem fp ? %s" % (f==fp(ca)))
print("MATCH COUNT:", sum(1 for _,f,_ in found if f==fp(ca)))
