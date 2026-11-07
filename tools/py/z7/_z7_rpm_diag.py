import json, os, socket
helper = r'''
import ctypes, ctypes.wintypes as w, subprocess, time, sys
k32 = ctypes.windll.kernel32
k32.OpenProcess.restype = w.HANDLE
k32.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
k32.ReadProcessMemory.restype = w.BOOL
k32.ReadProcessMemory.argtypes = [w.HANDLE, w.LPCVOID, w.LPVOID, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]

r = subprocess.run(["powershell","-NoProfile","-Command",
  "Get-Process -Name codoMP_client_shipRetail -ErrorAction SilentlyContinue | ForEach-Object { $_.Id }"], capture_output=True)
pids = [int(x) for x in r.stdout.decode().split() if x.strip().isdigit()]
print("game pids:", pids)
if not pids:
    print("NO_GAME"); sys.exit(0)

pid = pids[0]
for flags, label in [(0x0400|0x0010, "QUERY|VM_READ"),
                     (0x0010, "VM_READ only"),
                     (0x1F0FFF, "ALL_ACCESS")]:
    ctypes.set_last_error(0)
    h = k32.OpenProcess(flags, False, pid)
    err = ctypes.get_last_error()
    print("OpenProcess %-16s -> %s err=%d" % (label, h, err))
    if h:
        buf = ctypes.create_string_buffer(8)
        got = ctypes.c_size_t()
        ctypes.set_last_error(0)
        ok = k32.ReadProcessMemory(h, ctypes.c_void_p(0x84ABA50), buf, 4, ctypes.byref(got))
        e2 = ctypes.get_last_error()
        print("   ReadProcessMemory ok=%s err=%d got=%d bytes=%s" % (ok, e2, got.value, buf.raw[:4].hex()))
        k32.CloseHandle(h)
'''
STAGE=r"D:\z7tmp"; os.makedirs(STAGE, exist_ok=True)
hp=os.path.join(STAGE,"diag.py")
open(hp,"wb").write(helper.replace("\n","\r\n").encode("ascii"))
st=json.load(open(os.path.join("CODOLServer","logs","elevated_agent.json"),encoding="utf-8"))
req={"action":"run","argv":["python","-X","utf8",hp],"token":st["token"]}
s=socket.create_connection(("127.0.0.1",int(st["port"])),timeout=600)
s.sendall((json.dumps(req)+"\n").encode("utf-8"))
b=b""
while not b.endswith(b"\n"):
    c=s.recv(65536)
    if not c: break
    b+=c
r=json.loads(b.decode("utf-8"))
print(r.get("stdout"))
print((r.get("stderr") or "")[:400])
