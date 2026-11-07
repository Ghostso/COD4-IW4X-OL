from cryptography import x509
from cryptography.hazmat.primitives import serialization
import glob, os
for p in ["CODOLServer/lobby_server/lobby_ca.pem","CODOLServer/lobby_server/lobby_server.pem"]:
    if not os.path.isfile(p):
        print("MISSING", p); continue
    c = x509.load_pem_x509_certificate(open(p,"rb").read())
    print("="*60)
    print(p)
    print("  subject:", c.subject.rfc4514_string())
    print("  issuer :", c.issuer.rfc4514_string())
    try:
        san = c.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        print("  SAN    :", san.value.get_values_for_type(x509.DNSName))
    except Exception as e:
        print("  SAN    : (none)")
    try:
        bc = c.extensions.get_extension_for_class(x509.BasicConstraints)
        print("  CA     :", bc.value.ca, "pathlen:", bc.value.path_length)
    except Exception:
        print("  CA     : (no basicConstraints)")
