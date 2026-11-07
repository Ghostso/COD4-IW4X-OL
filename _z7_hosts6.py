# -*- coding: utf-8 -*-
"""Write hosts via copy-over. Helper is pure ASCII; paths passed via env."""
import json, os, socket

H = os.path.join(os.environ["windir"], "System32", "drivers", "etc", "hosts")
raw = open(H, "rb").read().decode("utf-8", "replace")
lines = [l for l in raw.splitlines() if "codol.qq.com" not in l]
lines.append("")
lines.append("# z7 codol local lobby")
lines.append("127.0.0.1 formal-zone-auth.codol.qq.com")
lines.append("127.0.0.2 formal-zone-lsg.codol.qq.com")
out = "\r\n".join(lines).rstrip() + "\r\n"

staged = os.path.join(os.getcwd(), "_z7_hosts_staged.txt")
open(staged, "wb").write(out.encode("utf-8"))
print("staged:", staged, len(out.encode()), "bytes")

helper = (
 'import os, shutil\n'
 'src = os.environ["Z7_SRC"]\n'
 'dst = os.path.join(os.environ["windir"], "System32", "drivers", "etc", "hosts")\n'
 'shutil.copy2(src, dst)\n'
 'back = open(dst, "rb").read().decode("utf-8", "replace")\n'
 'need = ["127.0.0.1 formal-zone-auth.codol.qq.com",\n'
 '        "127.0.0.2 formal-zone-lsg.codol.qq.com"]\n'
 'print("VERIFY:", all(n in back for n in need))\n'
 'for l in back.splitlines():\n'
 '    if l.strip() and not l.strip().startswith("#"):\n'
 '        print("LIVE>", l)\n'
 'print("HAS_down_qq:", "down.qq.com" in back)\n'
)
hp = os.path.join(os.getcwd(), "_z7_hosts_helper.py")
open(hp, "wb").write(helper.replace("\n", "\r\n").encode("ascii"))
print("helper written")

st = json.load(open(os.path.join("CODOLServer", "logs", "elevated_agent.json"), encoding="utf-8"))
req = {"action": "run", "argv": ["python", "-X", "utf8", hp], "token": st["token"],
       "env": {"Z7_SRC": staged}}
s = socket.create_connection(("127.0.0.1", int(st["port"])), timeout=600)
s.sendall((json.dumps(req) + "\n").encode("utf-8"))
buf = b""
while not buf.endswith(b"\n"):
    c = s.recv(65536)
    if not c: break
    buf += c
r = json.loads(buf.decode("utf-8"))
print("rc:", r.get("rc"))
print(r.get("stdout"))
print((r.get("stderr") or "")[:400])
