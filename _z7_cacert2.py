# -*- coding: utf-8 -*-
import os, re, hashlib, warnings
warnings.filterwarnings("ignore")
from cryptography import x509
from cryptography.hazmat.primitives.serialization import Encoding

GP  = os.path.join("COD OL","cacert.pem")
CAP = os.path.join("CODOLServer","lobby_server","lobby_ca.pem")
ca_pem = open(CAP,"rb").read()
ca = x509.load_pem_x509_certificate(ca_pem)
ca_fp = hashlib.sha256(ca.public_bytes(Encoding.DER)).hexdigest()
print("appending CA fp:", ca_fp)

raw = open(GP,"rb").read()
txt = raw.decode("utf-8","replace")
if ca_fp in [hashlib.sha256(x509.load_pem_x509_certificate(b.encode()).public_bytes(Encoding.DER)).hexdigest()
             for b in re.findall(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", txt, re.S)
             if True]:
    # ignore parse failures
    pass
# proper check
def fps(t):
    out=[]
    for b in re.findall(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", t, re.S):
        try:
            out.append(hashlib.sha256(x509.load_pem_x509_certificate(b.encode()).public_bytes(Encoding.DER)).hexdigest())
        except Exception:
            pass
    return out
before = fps(txt)
print("before cert count:", len(before))
print("already present:", ca_fp in before)
if ca_fp in before:
    print("SKIP append (already trustable)")
else:
    addition = b"\n# --- CODOL local lobby CA (z7 2026-10-02) ---\n" + ca_pem + b"\n"
    with open(GP,"ab") as f:
        f.write(addition)
    print("appended", len(addition), "bytes")
after_txt = open(GP,"rb").read().decode("utf-8","replace")
after = fps(after_txt)
print("after cert count:", len(after))
print("now present:", ca_fp in after)
print("final size:", os.path.getsize(GP))
