# -*- coding: utf-8 -*-
import os, io, re, subprocess, sys
GR = os.path.join("CODOLServer", "lobby_server")
for n in os.listdir(GR):
    if n.endswith((".pem",".crt",".cer",".key")):
        print("FILE", n, os.path.getsize(os.path.join(GR,n)))

def openssl(args):
    try:
        r = subprocess.run(["openssl"]+args, capture_output=True, text=True, timeout=20)
        return r.stdout + r.stderr
    except Exception as e:
        return "ERR " + str(e)

print("\n===== openssl present? =====")
print(openssl(["version"])[:200])
