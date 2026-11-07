# -*- coding: utf-8 -*-
"""Can we still produce SHA-1 signatures at all with this cryptography?"""
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes as H
import cryptography

print("cryptography:", cryptography.__version__)
k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
try:
    sig = k.sign(b"hello", padding.PKCS1v15(), H.SHA1())
    print("raw SHA1 sign:", len(sig), "bytes -> OK")
except Exception as e:
    print("raw SHA1 sign FAILED:", e)
# also test the Rust-side guard
try:
    from cryptography.hazmat.bindings._rust import x509 as rx
    print("rust x509 binding present")
except Exception as e:
    print("no rust binding:", e)
