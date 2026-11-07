# -*- coding: utf-8 -*-
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _015_lib import DATA, BASE
pats = [b"OpenSSL", b"conf_def", b"SSLv3", b"TLSv1", b"mbedTLS", b"wolfSSL",
        b"DTLS1_", b"secp224", b"OCSP", b"X509", b"ASN1", b"BN_mod", b"EVP_"]
for p in pats:
    n, first = 0, None
    i = DATA.find(p)
    while i >= 0:
        n += 1
        if first is None: first = i
        i = DATA.find(p, i + 1)
    print("%-10s count=%-5d first=0x%08X" % (p.decode(), n, BASE + first if first is not None else 0))
