# -*- coding: utf-8 -*-
"""Can our server actually negotiate the suites the client offered?"""
import ssl, socket, threading, time

CLIENT_SUITES = [0x39,0x38,0x35,0x33,0x32,0x2F,0x16,0x13,0x0A]
print("client offered:", ["0x%04X"%c for c in CLIENT_SUITES])

ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ctx.load_cert_chain(r"CODOLServer\lobby_server\lobby_server.pem",
                    r"CODOLServer\lobby_server\lobby_server.key")
try:
    ctx.set_ciphers("ALL:COMPLEMENTOFALL:@SECLEVEL=0")
except Exception as e:
    print("set_ciphers:", e)
ctx.minimum_version = ssl.TLSVersion.TLSv1
ctx.maximum_version = ssl.TLSVersion.TLSv1_2

got = {c["id"]: c["name"] for c in ctx.get_ciphers()}
print("\n=== do we have the client's suites? ===")
for sid in CLIENT_SUITES:
    nm = got.get(sid)
    print("  0x%04X %-40s %s" % (sid, nm or "(NOT AVAILABLE)", "OK" if nm else "*** MISSING ***"))
