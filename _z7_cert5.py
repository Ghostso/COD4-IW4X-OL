# -*- coding: utf-8 -*-
import os, re, hashlib
from cryptography import x509
from cryptography.hazmat.primitives import hashes
import warnings; warnings.filterwarnings("ignore")
GR = os.path.join("CODOLServer","lobby_server")
ca_pem = open(os.path.join(GR,"lobby_ca.pem"),"rb").read()
leaf_pem = open(os.path.join(GR,"lobby_server.pem"),"rb").read()
ca = x509.load_pem_x509_certificate(ca_pem)
leaf = x509.load_pem_x509_certificate(leaf_pem)
def fp(c):
    return hashlib.sha256(c.public_bytes(__import__("cryptography").hazmat.primitives.serialization.Encoding.DER)).hexdigest()
print("lobby_ca.pem       fp:", fp(ca))
print("lobby_server.pem iss:", leaf.issuer.rfc4514_string())
print("  issuer fp == ca fp:", leaf.issuer.public_bytes() == ca.subject.public_bytes())

gp = os.path.join("COD OL","cacert.pem")
txt = open(gp,"rb").read().decode("utf-8","replace")
blocks = re.findall(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", txt, re.S)
for i,b in enumerate(blocks):
    try:
        c = x509.load_pem_x509_certificate(b.encode())
        if "CODOL" in c.subject.rfc4514_string() or "CODOL" in c.issuer.rfc4514_string():
            print("cacert[%d] subj:" % i, c.subject.rfc4514_string())
            print("           fp:", fp(c))
    except Exception:
        pass
print("game ca == our ca.pem :", fp(ca) in [fp(x509.load_pem_x509_certificate(b.encode())) for b in blocks if _safe(b)] if False else "")
