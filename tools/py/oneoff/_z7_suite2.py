# -*- coding: utf-8 -*-
import ssl
print("python ssl:", ssl.OPENSSL_VERSION)
for spec in ["AES256-SHA", "DEFAULT@SECLEVEL=0", "ALL:@SECLEVEL=0",
             "RSA+AES256+SHA", "AES256-SHA:AES128-SHA:DES-CBC3-SHA",
             "HIGH:MEDIUM:!aNULL:!eNULL:@SECLEVEL=0"]:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    try:
        ctx.set_ciphers(spec)
        cs = ctx.get_ciphers()
        names = [c["name"] for c in cs]
        has35 = any(c["id"]==0x35 for c in cs)
        has2f = any(c["id"]==0x2F for c in cs)
        has0a = any(c["id"]==0x0A for c in cs)
        print("  %-46s n=%-4d 0x35=%s 0x2F=%s 0x0A=%s" % (spec, len(cs), has35, has2f, has0a))
    except Exception as e:
        print("  %-46s ERR %s" % (spec, e))
print()
# check openssl providers
try:
    import ssl
    print("legacy provider probe:")
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    import ctypes.util
    print("  openssl lib:", ctypes.util.find_library("ssl"))
except Exception as e:
    print("  ", e)
