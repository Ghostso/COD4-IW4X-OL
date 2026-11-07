from cryptography import x509
c = x509.load_pem_x509_certificate(open(r"D:\z7tmp\cert_sha1\ca.pem","rb").read())
bc = c.extensions.get_extension_for_class(x509.BasicConstraints).value
ku = c.extensions.get_extension_for_class(x509.KeyUsage).value
print("  subject   :", c.subject.rfc4514_string())
print("  CA        :", bc.ca, " pathlen:", bc.path_length)
print("  keyCertSign:", ku.key_cert_sign)
print("  sig       :", c.signature_algorithm_oid._name)
