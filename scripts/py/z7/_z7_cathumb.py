from cryptography import x509
import hashlib
c = x509.load_pem_x509_certificate(open(r"D:\z7tmp\cert_sha1\ca.pem","rb").read())
der = c.public_bytes(__import__("cryptography.hazmat.primitives.serialization", fromlist=["Encoding"]).Encoding.DER)
print("SHA1 thumbprint:", hashlib.sha1(der).hexdigest().upper())
print("subject:", c.subject.rfc4514_string())
