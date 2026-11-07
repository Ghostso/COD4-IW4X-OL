# -*- coding: utf-8 -*-
import os, io
GR = os.path.join("CODOLServer", "lobby_server")
def show(name, kind):
    p = os.path.join(GR, name)
    data = open(p, "rb").read()
    try:
        from cryptography import x509
        c = x509.load_pem_x509_certificate(data)
        print("="*72); print(name)
        print("  subject :", c.subject.rfc4514_string())
        print("  issuer  :", c.issuer.rfc4514_string())
        print("  notbefore:", c.not_valid_before_utc)
        print("  notafter :", c.not_valid_after_utc)
        try:
            bc = c.extensions.get_extension_for_class(x509.BasicConstraints).value
            print("  basicconstraints: ca=%s pathlen=%s" % (bc.ca, bc.path_length))
        except Exception as e:
            print("  basicconstraints: <none>", e)
        try:
            san = c.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
            print("  SAN:")
            for g in san:
                print("     ", type(g).__name__, g.value)
        except Exception as e:
            print("  SAN: <none>", e)
        try:
            ku = c.extensions.get_extension_for_class(x509.KeyUsage).value
            print("  keyusage: keyCertSign=%s cRLSign=%s digitalSignature=%s keyEncipherment=%s" % (
                ku.key_cert_sign, ku.crl_sign, ku.digital_signature, ku.key_encipherment))
        except Exception as e:
            print("  keyusage: <none>", e)
    except Exception as e:
        print("="*72); print(name, "PARSE FAIL:", e)

show("lobby_ca.pem", "ca")
show("lobby_server.pem", "leaf")
print("="*72)
print("ca_append.pem vs lobby_ca.pem identical:", open(os.path.join(GR,"ca_append.pem"),"rb").read() == open(os.path.join(GR,"lobby_ca.pem"),"rb").read())
