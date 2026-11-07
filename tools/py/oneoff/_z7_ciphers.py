# -*- coding: utf-8 -*-
import ssl
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
try:
    ctx.set_ciphers("ALL:COMPLEMENTOFALL:@SECLEVEL=0")
except Exception as e:
    print("set_ciphers err:", e)
ctx.minimum_version = ssl.TLSVersion.TLSv1
ctx.maximum_version = ssl.TLSVersion.TLSv1_2
cs = ctx.get_ciphers()
print("total ciphers:", len(cs))
# look for the documented one
target = [c for c in cs if "AES256-SHA" == c["name"] or c["name"] == "AES256-SHA"]
print("\n=== AES256-SHA (documented success) present? ===")
for c in target:
    print("  ", c)
print("\n=== all ciphers mentioning AES256 ===")
for c in cs:
    if "AES256" in c["name"]:
        print("  %-38s proto=%-8s kx=%s auth=%s" % (c["name"], c.get("protocol"), c.get("kx"), c.get("auth")))
print("\n=== TLS1.0-capable ciphers (first 25) ===")
n=0
for c in cs:
    if str(c.get("protocol")) in ("TLSv1","SSLv3") or "TLSv1" in str(c.get("protocol","")):
        print("  %-38s proto=%-8s kx=%-10s" % (c["name"], c.get("protocol"), c.get("kx")))
        n+=1
        if n>=25: break
print("(tls1.0-flagged count:", n, ")")
