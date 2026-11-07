# -*- coding: utf-8 -*-
"""Generate a root CA + leaf per CODOL_LOBBY_WORKING_20261002.md section 2 item 4.

Requirements from the doc:
  * root CA must carry basicConstraints CA=TRUE, pathlength=0
  * leaf SAN must include localhost, formal-zone-auth.codol.qq.com,
    formal-zone-lsg.codol.qq.com
  * the CA must be installed into LocalMachine\\Root AND appended to the game's
    cacert.pem (the append is done separately, as a file write)

Writes into this directory: codol_ca.pem / codol_ca.key / codol_leaf.pem /
codol_leaf.key.  Idempotent only in the sense that it overwrites.
"""
import argparse
import datetime
import ipaddress
import os

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


DNS_NAMES = [
    "localhost",
    "formal-zone-auth.codol.qq.com",
    "formal-zone-lsg.codol.qq.com",
]


def make_ca():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "CODOL-LOCAL"),
        x509.NameAttribute(NameOID.COMMON_NAME, "CODOL Local Lobby CA"),
    ])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0),
                       critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True, content_commitment=False,
                key_encipherment=False, data_encipherment=False,
                key_agreement=False, key_cert_sign=True, crl_sign=True,
                encipher_only=False, decipher_only=False),
            critical=True)
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(key.public_key()),
            critical=False)
        .sign(key, hashes.SHA256())
    )
    return key, cert


def make_leaf(ca_key, ca_cert):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "CODOL-LOCAL"),
        x509.NameAttribute(NameOID.COMMON_NAME, "formal-zone-auth.codol.qq.com"),
    ])
    now = datetime.datetime.now(datetime.timezone.utc)
    san = x509.SubjectAlternativeName(
        [x509.DNSName(d) for d in DNS_NAMES] +
        [x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
         x509.IPAddress(ipaddress.IPv4Address("127.0.0.2"))])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None),
                       critical=True)
        .add_extension(san, critical=False)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True, content_commitment=False,
                key_encipherment=True, data_encipherment=False,
                key_agreement=False, key_cert_sign=False, crl_sign=False,
                encipher_only=False, decipher_only=False),
            critical=True)
        .add_extension(
            x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=False)
        .sign(ca_key, hashes.SHA256())
    )
    return key, cert


def write(path, data):
    with open(path, "wb") as f:
        f.write(data)
    print("  wrote %s (%d bytes)" % (path, len(data)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.dirname(os.path.abspath(__file__)))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    ca_key, ca_cert = make_ca()
    leaf_key, leaf_cert = make_leaf(ca_key, ca_cert)

    print("generating into %s" % a.out)
    write(os.path.join(a.out, "codol_ca.key"),
          ca_key.private_bytes(serialization.Encoding.PEM,
                               serialization.PrivateFormat.TraditionalOpenSSL,
                               serialization.NoEncryption()))
    write(os.path.join(a.out, "codol_ca.pem"),
          ca_cert.public_bytes(serialization.Encoding.PEM))
    write(os.path.join(a.out, "codol_leaf.key"),
          leaf_key.private_bytes(serialization.Encoding.PEM,
                                 serialization.PrivateFormat.TraditionalOpenSSL,
                                 serialization.NoEncryption()))
    write(os.path.join(a.out, "codol_leaf.pem"),
          leaf_cert.public_bytes(serialization.Encoding.PEM))

    der = ca_cert.public_bytes(serialization.Encoding.DER)
    import hashlib
    tp = hashlib.sha1(der).hexdigest().upper()
    print()
    print("CA SHA1 thumbprint: %s" % tp)
    print("CA subject        : %s" % ca_cert.subject.rfc4514_string())
    print("leaf SAN          : %s" % DNS_NAMES)


if __name__ == "__main__":
    main()
