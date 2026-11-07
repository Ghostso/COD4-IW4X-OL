from cryptography import x509
import re
raw = open(r"run_codol_001\sandbox_datafix_20260929\cacert.pem","rb").read()
blocks = re.findall(rb"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", raw, re.S)
found = any("CODOL-LOCAL" in (lambda b: x509.load_pem_x509_certificate(b+b"\n").subject.rfc4514_string())(b)
            for b in blocks if b)
print("certs:", len(blocks), " CODOL CA present:", found)
