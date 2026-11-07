"""Generate a self-signed CA + server cert for the local CODOL lobby.

ASCII only. Run:  python -X utf8 mklobby_cert.py <outdir>
Writes:
  <outdir>/lobby_ca.pem      self-signed CA (public)
  <outdir>/lobby_ca.key      CA private key
  <outdir>/lobby_server.pem  server cert (leaf, signed by CA, CN=127.0.0.1)
  <outdir>/lobby_server.key  server private key
  <outdir>/ca_append.pem     block to append to the game's cacert.pem
No system trust store is touched. No network settings are touched.
"""
import os
import sys
import datetime

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def newkey():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def algo(sha1):
    return hashes.SHA1() if sha1 else hashes.SHA256()


def w(path, data):
    with open(path, "wb") as f:
        f.write(data)


def main():
    args = [a for a in sys.argv[1:] if a != "--sha1"]
    sha1 = "--sha1" in sys.argv
    out = args[0] if args else "."
    os.makedirs(out, exist_ok=True)
    now = datetime.datetime.now(datetime.timezone.utc)

    ca_key = newkey()
    ca_name = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "CODOL Local Lobby CA"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "CODOL-LOCAL"),
    ])
    ca = (
        x509.CertificateBuilder()
        .subject_name(ca_name)
        .issuer_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True, content_commitment=False,
                key_encipherment=False, data_encipherment=False,
                key_agreement=False, key_cert_sign=True, crl_sign=True,
                encipher_only=False, decipher_only=False,
            ),
            critical=True,
        )
        .sign(ca_key, algo(sha1))
    )

    srv_key = newkey()
    srv = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "CODOL-LOCAL"),
        ]))
        .issuer_name(ca_name)
        .public_key(srv_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.SubjectAlternativeName([
                x509.IPAddress(__import__("ipaddress").ip_address("127.0.0.1")),
                # The client connects to the lobby host 127.0.0.2 (dwauth.ini
                # field 3) while /auth/ uses 127.0.0.1.  Both must be in the
                # SAN or cURL's VERIFYHOST=2 rejects the lobby connection and
                # the client falls back to the GET / cert-probe, which is
                # exactly the "无法连接大厅服务" path.
                x509.IPAddress(__import__("ipaddress").ip_address("127.0.0.2")),
                x509.DNSName("localhost"),
                # The working document routes by HOSTNAME via the hosts file
                # (formal-zone-auth -> 127.0.0.1, formal-zone-lsg -> 127.0.0.2),
                # so the client's TLS layer verifies against the NAME, not the
                # IP.  Without these two SANs VERIFYHOST fails and the client
                # falls back to the cert-probe GET, which is the
                # "cannot connect to lobby service" dialog.
                x509.DNSName("formal-zone-auth.codol.qq.com"),
                x509.DNSName("formal-zone-lsg.codol.qq.com"),
            ]),
            critical=False,
        )
        .add_extension(
            x509.ExtendedKeyUsage([
                x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
            ]),
            critical=False,
        )
        .sign(ca_key, algo(sha1))
    )

    w(os.path.join(out, "lobby_ca.pem"),
      ca.public_bytes(serialization.Encoding.PEM))
    w(os.path.join(out, "lobby_ca.key"),
      ca_key.private_bytes(serialization.Encoding.PEM,
                           serialization.PrivateFormat.TraditionalOpenSSL,
                           serialization.NoEncryption()))
    w(os.path.join(out, "lobby_server.pem"),
      srv.public_bytes(serialization.Encoding.PEM))
    w(os.path.join(out, "lobby_server.key"),
      srv_key.private_bytes(serialization.Encoding.PEM,
                            serialization.PrivateFormat.TraditionalOpenSSL,
                            serialization.NoEncryption()))
    w(os.path.join(out, "ca_append.pem"),
      b"\n# --- CODOL local lobby CA ---\n" + ca.public_bytes(serialization.Encoding.PEM))

    print("wrote to " + os.path.abspath(out))
    print("  lobby_ca.pem / lobby_ca.key")
    print("  lobby_server.pem / lobby_server.key  (CN=127.0.0.1, SAN IP:127.0.0.1)")
    print("  signature algorithm: %s" % ("SHA1" if sha1 else "SHA256"))
    print("  ca_append.pem  <- append this to the game's cacert.pem")


if __name__ == "__main__":
    main()
