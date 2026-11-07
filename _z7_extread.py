# -*- coding: utf-8 -*-
"""External read of the DW lobby state machine addresses.
No observer change required. Runs elevated via the agent."""
import json, os, socket, sys

helper = r'''
import ctypes, ctypes.wintypes as w, subprocess, time, sys
k32 = ctypes.windll.kernel32
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010

k32.OpenProcess.restype = w.HANDLE
k32.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
k32.ReadProcessMemory.restype = w.BOOL
k32.ReadProcessMemory.argtypes = [w.HANDLE, w.LPCVOID, w.LPVOID, ctypes.c_size_t,
                                  ctypes.POINTER(ctypes.c_size_t)]

ADDRS = [
    (0x84ABA50, 4, "dwLobby_state"),
    (0x84ABA78, 4, "dns_result"),
    (0x84ABA5C, 4, "acct_code"),
    (0xE4EA3C,  4, "state_name_ptr"),
    (0x081A76A8, 64, "hostA@81A76A8"),
    (0x081A7F34, 64, "hostB@81A7F34"),
    (0x081A9EC4, 4, "port@81A9EC4"),
]
NAMES = {
    0xDE08C8: "dwLogonStart", 0xDE08D8: "DW_DNS_ERROR",
    0xDE08E8: "DW_DNS_COMPLETE", 0xDE08F8: "DW_ACCOUNT_ERROR",
    0xDE090C: "DW_ACCOUNT_LOGIN_COMPLETE", 0xDE0928: "DW_LOBBY_ERROR",
    0xDE0938: "DW_LOBBY_CONNECTED",
}

def pids():
    r = subprocess.run(["powershell","-NoProfile","-Command",
      "Get-Process -Name codoMP_client_shipRetail -ErrorAction SilentlyContinue | ForEach-Object { $_.Id }"],
      capture_output=True)
    return [int(x) for x in r.stdout.decode().split() if x.strip().isdigit()]

def rd(h, addr, n):
    buf = ctypes.create_string_buffer(n)
    got = ctypes.c_size_t()
    ok = k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, n, ctypes.byref(got))
    if not ok: return None
    return buf.raw[:got.value]

print("waiting for game process ...", flush=True)
h = None; pid = None
t0 = time.time()
while time.time() - t0 < 90:
    for p in pids():
        h2 = k32.OpenProcess(PROCESS_QUERY_INFORMATION|PROCESS_VM_READ, False, p)
        if h2:
            h = h2; pid = p
            break
    if h: break
    time.sleep(0.5)

if not h:
    print("GAME_NOT_FOUND"); sys.exit(2)
print("attached pid=%d handle=%s" % (pid, h), flush=True)

READ_FAIL = 0
t0 = time.time()
while time.time() - t0 < 130:
    row = []
    for addr, n, name in ADDRS:
        b = rd(h, addr, n)
        if b is None:
            READ_FAIL += 1
            row.append("%s=ERR" % name)
            continue
        if name == "state_name_ptr":
            v = int.from_bytes(b, "little")
            row.append("%s=0x%08X(%s)" % (name, v, NAMES.get(v, "?")))
        elif n == 4:
            row.append("%s=%d" % (name, int.from_bytes(b, "little")))
        else:
            s = b.split(b"\x00")[0]
            row.append("%s=%r" % (name, s[:48]))
    print("%.2f %s" % (time.time()-t0, " | ".join(row)), flush=True)
    time.sleep(0.5)

print("READ_FAIL_TOTAL=%d" % READ_FAIL)
'''

STAGE = r"D:\z7tmp"
os.makedirs(STAGE, exist_ok=True)
hp = os.path.join(STAGE, "ext_read.py")
open(hp, "wb").write(helper.replace("\n","\r\n").encode("ascii"))

st = json.load(open(os.path.join("CODOLServer","logs","elevated_agent.json"), encoding="utf-8"))
req = {"action":"run","argv":["python","-X","utf8",hp],"token":st["token"]}
s = socket.create_connection(("127.0.0.1", int(st["port"])), timeout=900)
s.sendall((json.dumps(req)+"\n").encode("utf-8"))
b = b""
while not b.endswith(b"\n"):
    c = s.recv(65536)
    if not c: break
    b += c
r = json.loads(b.decode("utf-8"))
print("rc:", r.get("rc"))
out = r.get("stdout") or ""
print(out[-3000:] if len(out) > 3000 else out)
err = r.get("stderr") or ""
if err: print("STDERR:", err[:600])
