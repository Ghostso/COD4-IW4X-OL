# -*- coding: utf-8 -*-
"""Append the two doc-required hosts lines. Preserve existing content.
Doc section 2 item 1: only these two; NEVER hijack down.qq.com / intldlgs.qq.com."""
import os, json, socket, shutil, time

H = os.path.join(os.environ["windir"], "System32", "drivers", "etc", "hosts")
NEED = ["127.0.0.1 formal-zone-auth.codol.qq.com",
        "127.0.0.2 formal-zone-lsg.codol.qq.com"]

raw = open(H, "rb").read()
print("current hosts (%d bytes):" % len(raw))
print(raw.decode("utf-8", "replace"))
print("----")

txt = raw.decode("utf-8", "replace")
lines = txt.splitlines()
missing = [n for n in NEED if n not in txt]

if not missing:
    print("both lines already present -> nothing to do")
else:
    add = "\r\n".join([""] + ["# z7 codol lobby redirect"] + missing) + "\r\n"
    new = txt.rstrip("\r\n") + add
    print("adding:")
    for m in missing:
        print("   " + m)
    # write via elevated agent (hosts needs admin)
    tmp = os.path.join(os.getcwd(), "_z7_hosts_new.txt")
    open(tmp, "w", encoding="utf-8", newline="").write(new)
    st = json.load(open(os.path.join("CODOLServer", "logs", "elevated_agent.json"), encoding="utf-8"))
    req = {"action": "run",
           "argv": ["cmd", "/c", "copy", "/Y", tmp, H],
           "token": st["token"]}
    s = socket.create_connection(("127.0.0.1", int(st["port"])), timeout=600)
    s.sendall((json.dumps(req) + "\n").encode("utf-8"))
    buf = b""
    while not buf.endswith(b"\n"):
        c = s.recv(65536)
        if not c: break
        buf += c
    print("agent reply:", buf.decode("utf-8", "replace")[:300])

print()
print("=== hosts after ===")
print(open(H, "rb").read().decode("utf-8", "replace"))
