from cryptography import x509
import re
for p in [r"run_codol_001\sandbox_ifs1_20260923\cacert.pem",
          r"COD OL\cacert.pem"]:
    raw = open(p,"rb").read()
    blocks = re.findall(rb"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", raw, re.S)
    found = False
    for b in blocks:
        try:
            c = x509.load_pem_x509_certificate(b+b"\n")
            if "CODOL-LOCAL" in c.subject.rfc4514_string():
                found = True
        except Exception:
            pass
    print("  %-52s certs=%-4d  CODOL_CA=%s" % (p, len(blocks), found))
