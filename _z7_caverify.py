from cryptography import x509
import re, os
for p in [r"COD OL\cacert.pem",
          r"run_codol_001\sandbox_ifs1_20260923\cacert.pem"]:
    raw = open(p, "rb").read()
    blocks = re.findall(rb"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----",
                        raw, re.S)
    found = None
    for b in blocks:
        try:
            c = x509.load_pem_x509_certificate(b + b"\n")
        except Exception:
            continue
        if "CODOL-LOCAL" in c.subject.rfc4514_string():
            found = c
    print("%-52s certs=%d  CODOL-CA-present=%s" % (p, len(blocks), bool(found)))
    if found:
        bc = found.extensions.get_extension_for_class(x509.BasicConstraints).value
        print("      subject=%s" % found.subject.rfc4514_string())
        print("      CA=%s pathlen=%s" % (bc.ca, bc.path_length))
