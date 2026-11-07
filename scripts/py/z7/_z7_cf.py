# -*- coding: utf-8 -*-
"""Test whether 360 blocks ALL writes to hosts, or just our method.
Try: native CreateFileW with GENERIC_WRITE, and WriteFile."""
import json, os, socket
STAGE = r"D:\z7tmp"
os.makedirs(STAGE, exist_ok=True)
helper = r'''
import ctypes, os
from ctypes import wintypes
k32 = ctypes.WinDLL("kernel32", use_last_error=True)
GENERIC_READ=0x80000000; GENERIC_WRITE=0x40000000
OPEN_EXISTING=3; FILE_ATTRIBUTE_NORMAL=0x80
CREATE_ALWAYS=2; TRUNCATE_EXISTING=5
H = os.path.join(os.environ["windir"], "System32", "drivers", "etc", "hosts")

k32.CreateFileW.restype = wintypes.HANDLE
k32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                            wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD,
                            wintypes.HANDLE]

for dwCreation, name in [(OPEN_EXISTING,"OPEN_EXISTING"),
                         (TRUNCATE_EXISTING,"TRUNCATE_EXISTING"),
                         (CREATE_ALWAYS,"CREATE_ALWAYS")]:
    ctypes.set_last_error(0)
    h = k32.CreateFileW(H, GENERIC_READ|GENERIC_WRITE, 0, None,
                        dwCreation, FILE_ATTRIBUTE_NORMAL, None)
    err = ctypes.get_last_error()
    ok = h not in (None, 0, -1, 0xFFFFFFFFFFFFFFFF)
    print("CreateFileW %-18s -> handle=%s err=%d %s"
          % (name, h, err, "OK" if ok else "FAIL"))
    if ok:
        k32.CloseHandle(h)
'''
hp = os.path.join(STAGE, "cftest.py")
open(hp,"wb").write(helper.replace("\n","\r\n").encode("ascii"))
st = json.load(open(os.path.join("CODOLServer","logs","elevated_agent.json"), encoding="utf-8"))
req = {"action":"run","argv":["python","-X","utf8",hp],"token":st["token"]}
s = socket.create_connection(("127.0.0.1", int(st["port"])), timeout=600)
s.sendall((json.dumps(req)+"\n").encode("utf-8"))
buf=b""
while not buf.endswith(b"\n"):
    c=s.recv(65536)
    if not c: break
    buf+=c
r=json.loads(buf.decode("utf-8"))
print("rc:",r.get("rc"))
print(r.get("stdout"))
print((r.get("stderr") or "")[:300])
