# -*- coding: utf-8 -*-
"""Launch game, wait until process exists, then immediately diagnose RPM."""
import json, os, socket, subprocess, threading, time

ROOT = os.getcwd()
st = json.load(open(os.path.join(ROOT,"CODOLServer","logs","elevated_agent.json"), encoding="utf-8"))

DIAG = r'''
import ctypes, ctypes.wintypes as w, subprocess, sys, time
k32 = ctypes.windll.kernel32
k32.OpenProcess.restype = w.HANDLE
k32.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
k32.ReadProcessMemory.restype = w.BOOL
k32.ReadProcessMemory.argtypes = [w.HANDLE, w.LPCVOID, w.LPVOID, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]

def pids():
    r = subprocess.run(["powershell","-NoProfile","-Command",
      "Get-Process -Name codoMP_client_shipRetail -ErrorAction SilentlyContinue | ForEach-Object { $_.Id }"], capture_output=True)
    return [int(x) for x in r.stdout.decode().split() if x.strip().isdigit()]

print("waiting for game ...", flush=True)
pid = None
t0 = time.time()
while time.time()-t0 < 60:
    p = pids()
    if p: pid = p[0]; break
    time.sleep(0.3)
if not pid:
    print("NO_GAME"); sys.exit(0)
print("game pid:", pid, flush=True)

ctypes.set_last_error(0)
h = k32.OpenProcess(0x0400|0x0010, False, pid)
print("OpenProcess -> %s err=%d" % (h, ctypes.get_last_error()), flush=True)
if not h: sys.exit(0)

ADDRS = [(0x84ABA50,"dwLobby_state",4),(0x84ABA78,"dns_result",4),
         (0x84ABA5C,"acct_code",4),(0xE4EA3C,"state_name_ptr",4),
         (0x081A76A8,"hostA",64),(0x081A7F34,"hostB",64),(0x081A9EC4,"port",4)]
NAMES={0xDE08C8:"dwLogonStart",0xDE08D8:"DW_DNS_ERROR",0xDE08E8:"DW_DNS_COMPLETE",
       0xDE08F8:"DW_ACCOUNT_ERROR",0xDE090C:"DW_ACCOUNT_LOGIN_COMPLETE",
       0xDE0928:"DW_LOBBY_ERROR",0xDE0938:"DW_LOBBY_CONNECTED"}
t0=time.time(); fails=0
while time.time()-t0 < 130:
    if not pids():
        print("game exited", flush=True); break
    row=[]
    for addr,name,n in ADDRS:
        buf=ctypes.create_string_buffer(n); got=ctypes.c_size_t()
        ctypes.set_last_error(0)
        ok=k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, n, ctypes.byref(got))
        if not ok:
            fails+=1; row.append("%s=ERR(%d)"%(name,ctypes.get_last_error())); continue
        if name=="state_name_ptr":
            v=int.from_bytes(buf.raw[:4],"little")
            row.append("%s=0x%08X(%s)"%(name,v,NAMES.get(v,"?")))
        elif n==4:
            row.append("%s=%d"%(name,int.from_bytes(buf.raw[:4],"little")))
        else:
            row.append("%s=%r"%(name,buf.raw.split(b"\x00")[0][:40]))
    print("%.2f %s"%(time.time()-t0," | ".join(row)), flush=True)
    time.sleep(0.5)
print("FAILS=%d"%fails, flush=True)
'''

STAGE = r"D:\z7tmp"; os.makedirs(STAGE, exist_ok=True)
hp = os.path.join(STAGE,"diag2.py")
open(hp,"wb").write(DIAG.replace("\n","\r\n").encode("ascii"))

def launch():
    LD = os.path.join(ROOT,"CODOLServer","logs","Z7_3074"); os.makedirs(LD, exist_ok=True)
    argv = ["powershell","-NoProfile","-ExecutionPolicy","Bypass","-File",
        os.path.join("run_codol_001","elevated_ifs1_observer.ps1"),
        "-DurationSeconds","160",
        "-Sandbox", os.path.join(ROOT,"run_codol_001","sandbox_datafix_20260929"),
        "-TenProxyShm", os.path.join(ROOT,"CODOLServer","_subagents","_tenproxy_shm_fixed.bin"),
        "-PokeLobbyHost","127.0.0.1","-PokeLobbyPort","8443",
        "-PokeE57","0x00E57A5A","-PokeLobbyGlobals","1","-LobbyReadyOnly","1",
        "-Post83Trace","1","-Post83Seconds","90",
        "-HandshakeReadyFile", os.path.join(LD,"ready.flag"),
        "-HandshakeEchoFile", os.path.join(LD,"echo.txt"),
        "-PatchDelay","42","-Patch85Pass","1"]
    req = {"action":"run","argv":argv,"token":st["token"]}
    s = socket.create_connection(("127.0.0.1", int(st["port"])), timeout=900)
    s.sendall((json.dumps(req)+"\n").encode("utf-8"))
    b=b""
    while not b.endswith(b"\n"):
        c=s.recv(65536)
        if not c: break
        b+=c

threading.Thread(target=launch, daemon=True).start()
time.sleep(3)

req = {"action":"run","argv":["python","-X","utf8",hp],"token":st["token"]}
s = socket.create_connection(("127.0.0.1", int(st["port"])), timeout=900)
s.sendall((json.dumps(req)+"\n").encode("utf-8"))
b=b""
while not b.endswith(b"\n"):
    c=s.recv(65536)
    if not c: break
    b+=c
r=json.loads(b.decode("utf-8"))
out = r.get("stdout") or ""
print(out[:4000])
print("...")
print(out[-1500:] if len(out)>4000 else "")
print("STDERR:", (r.get("stderr") or "")[:400])
