import json, os, socket
STAGE = r"D:\z7tmp"
helper = r'''
import ctypes, os
from ctypes import wintypes
k32 = ctypes.WinDLL("kernel32", use_last_error=True)
GENERIC_READ=0x80000000; GENERIC_WRITE=0x40000000
OPEN_EXISTING=3; FILE_ATTRIBUTE_NORMAL=0x80
H = os.path.join(os.environ["windir"], "System32", "drivers", "etc", "hosts")
k32.CreateFileW.restype = wintypes.HANDLE
k32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                            wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
k32.ReadFile.argtypes=[wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
                       ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
k32.WriteFile.argtypes=[wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
                        ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
k32.SetFilePointer.argtypes=[wintypes.HANDLE, wintypes.LONG, wintypes.LPVOID, wintypes.DWORD]
k32.SetEndOfFile.argtypes=[wintypes.HANDLE]
h = k32.CreateFileW(H, GENERIC_READ|GENERIC_WRITE, 0, None, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, None)
buf = ctypes.create_string_buffer(1<<20); n = wintypes.DWORD()
k32.ReadFile(h, buf, 1<<20, ctypes.byref(n), None)
txt = buf.raw[:n.value].decode("utf-8","replace")
lines = [l for l in txt.splitlines() if "codol.qq.com" not in l]
new = ("\r\n".join(lines).rstrip() + "\r\n").encode("utf-8")
k32.SetFilePointer(h, 0, None, 0)
w = wintypes.DWORD()
k32.WriteFile(h, new, len(new), ctypes.byref(w), None)
k32.SetEndOfFile(h); k32.CloseHandle(h)
print("removed codol lines; hosts now", os.path.getsize(H), "bytes")
for l in open(H,"rb").read().decode("utf-8","replace").splitlines():
    if l.strip() and not l.strip().startswith("#"): print("LIVE>", l)
'''
hp = os.path.join(STAGE,"hosts_rm.py")
open(hp,"wb").write(helper.replace("\n","\r\n").encode("ascii"))
st = json.load(open(os.path.join("CODOLServer","logs","elevated_agent.json"), encoding="utf-8"))
req={"action":"run","argv":["python","-X","utf8",hp],"token":st["token"]}
s=socket.create_connection(("127.0.0.1",int(st["port"])),timeout=600)
s.sendall((json.dumps(req)+"\n").encode("utf-8"))
b=b""
while not b.endswith(b"\n"):
    c=s.recv(65536)
    if not c: break
    b+=c
print(json.loads(b.decode("utf-8")).get("stdout"))
