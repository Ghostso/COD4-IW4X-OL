# -*- coding: utf-8 -*-
"""Check the auth server's cert/key pair and SAN."""
from cryptography import x509
from cryptography.hazmat.primitives import serialization
import os
LS = r"CODOLServer\lobby_server"
cert = os.path.join(LS, "lobby_server.pem")
key  = os.path.join(LS, "lobby_server.key")
c = x509.load_pem_x509_certificate(open(cert,"rb").read())
k = serialization.load_pem_private_key(open(key,"rb").read(), password=None)
print("cert subject:", c.subject.rfc4514_string())
print("cert issuer :", c.issuer.rfc4514_string())
try:
    san = c.extensions.get_extension_for_class(x509.SubjectAlternativeName)
    print("SAN dns   :", san.value.get_values_for_type(x509.DNSName))
    print("SAN ip    :", san.value.get_values_for_type(x509.IPAddress))
except Exception as e:
    print("SAN: none", e)
# key match?
pub_c = c.public_key().public_numbers()
pub_k = k.public_key().public_numbers()
print("key matches cert:", pub_c == pub_k)
print("valid from:", c.not_valid_before_utc, "to:", c.not_valid_after_utc)
# sig algo
print("sig algo:", c.signature_algorithm_oid._name)
