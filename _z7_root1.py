# -*- coding: utf-8 -*-
import os, subprocess, hashlib, warnings
warnings.filterwarnings("ignore")
from cryptography import x509
from cryptography.hazmat.primitives.serialization import Encoding

CAP = os.path.join("CODOLServer","lobby_server","lobby_ca.pem")
ca = x509.load_pem_x509_certificate(open(CAP,"rb").read())
ca_fp = hashlib.sha256(ca.public_bytes(Encoding.DER)).hexdigest()
print("CA fp:", ca_fp)
print("CA thumbprint(sha1):", hashlib.sha1(ca.public_bytes(Encoding.DER)).hexdigest().upper())

r = subprocess.run(["certutil","-addstore","-f","Root",CAP], capture_output=True, text=True)
print("rc:", r.returncode)
print(r.stdout[-1500:])
print("STDERR:", r.stderr[-800:])
