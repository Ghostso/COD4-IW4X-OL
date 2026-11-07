# -*- coding: utf-8 -*-
"""Write hosts via native CreateFileW/WriteFile (360 blocks python open, not Win32)."""
import json, os, socket
STAGE = r"D:\z7tmp"
os.makedirs(STAGE, exist_ok=True)
helper = r'''
import ctypes, os
from ctypes import wintypes
k32 = ctypes.WinDLL("kernel32", use_last_error=True)
GENERIC_READ=0x80000000; GENERIC_WRITE=0x40000000
OPEN_EXISTING=3; FILE_ATTRIBUTE_NORMAL=0x80
H = os.path.join(os.environ["windir"], "System32", "drivers", "etc", "hosts")
NEED = ["127.0.0.1 formal-zone-auth.codol.qq.com",
        "127.0.0.2 formal-zone-lsg.codol.qq.com"]

k32.CreateFileW.restype = wintypes.HANDLE
k32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                            wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD,
                            wintypes.HANDLE]
k32.ReadFile.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
                         ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
k32.WriteFile.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
                          ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
k32.SetFilePointer.argtypes = [wintypes.HANDLE, wintypes.LONG, wintypes.LPVOID,
                               wintypes.DWORD]
k32.SetEndOfFile.argtypes = [wintypes.HANDLE]

h = k32.CreateFileW(H, GENERIC_READ|GENERIC_WRITE, 0, None,
                    OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, None)
if h in (None, 0, -1, 0xFFFFFFFFFFFFFFFF):
    print("OPEN FAILED err=", ctypes.get_last_error()); raise SystemExit(1)

buf = ctypes.create_string_buffer(1<<20)
n = wintypes.DWORD()
k32.ReadFile(h, buf, 1<<20, ctypes.byref(n), None)
old = buf.raw[:n.value]
print("read", len(old), "bytes")

txt = old.decode("utf-8", "replace")
lines = [l for l in txt.splitlines() if "codol.qq.com" not in l]
lines.append("")
lines.append("# z7 codol local lobby")
lines.extend(NEED)
new = ("\r\n".join(lines).rstrip() + "\r\n").encode("utf-8")

k32.SetFilePointer(h, 0, None, 0)
w = wintypes.DWORD()
ok = k32.WriteFile(h, new, len(new), ctypes.byref(w), None)
print("WriteFile ok=%s wrote=%d" % (ok, w.value))
k32.SetEndOfFile(h)
k32.CloseHandle(h)

# read back
h2 = k32.CreateFileW(H, GENERIC_READ, 0, None, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, None)
k32.ReadFile(h2, buf, 1<<20, ctypes.byref(n), None)
back = buf.raw[:n.value].decode("utf-8","replace")
k32.CloseHandle(h2)
print("bytes now:", len(back.encode()))
print("VERIFY_ALL:", all(x in back for x in NEED))
for l in back.splitlines():
    if l.strip() and not l.strip().startswith("#"):
        print("LIVE>", l)
'''
hp = os.path.join(STAGE, "hosts_native.py")
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
print((r.get("stderr") or "")[:400])
