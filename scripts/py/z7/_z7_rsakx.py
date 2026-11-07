import ssl
print("OPENSSL_VERSION:", ssl.OPENSSL_VERSION)
print("has TLSVersion:", hasattr(ssl, "TLSVersion"))
# list every cipher the runtime knows, grep for RSA-kx ones
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
try: ctx.set_ciphers("ALL:COMPLEMENTOFALL:@SECLEVEL=0")
except Exception as e: print("set_ciphers:", e)
rsa_kx = [c for c in ctx.get_ciphers() if c.get("kea") == "kx-rsa" or c.get("kx") == "RSA"]
print("RSA-kx ciphers available:", len(rsa_kx))
for c in rsa_kx[:20]:
    print("   ", c["name"], "id=0x%04X" % c["id"])
