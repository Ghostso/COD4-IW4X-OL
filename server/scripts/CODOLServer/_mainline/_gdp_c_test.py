"""C test: fake GDP/TQoS HTTP server + game launch + state sampling."""
import ctypes, ctypes.wintypes as wt, json, os, socket, struct, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

k32=ctypes.WinDLL("kernel32",use_last_error=True); adv=ctypes.WinDLL("advapi32",use_last_error=True)
class LUID(ctypes.Structure): _fields_=[("L",wt.DWORD),("H",wt.LONG)]
class LAA(ctypes.Structure): _fields_=[("Luid",LUID),("Attr",wt.DWORD)]
class TP(ctypes.Structure): _fields_=[("n",wt.DWORD),("p",LAA*1)]
class SI(ctypes.Structure):
    _fields_=[("cb",wt.DWORD),("r",wt.LPWSTR),("d",wt.LPWSTR),("t",wt.LPWSTR),("x",wt.DWORD),("y",wt.DWORD),
              ("xs",wt.DWORD),("ys",wt.DWORD),("xc",wt.DWORD),("yc",wt.DWORD),("fa",wt.DWORD),("fl",wt.DWORD),
              ("sw",wt.WORD),("cr",wt.WORD),("rp",ctypes.c_void_p),("hi",wt.HANDLE),("ho",wt.HANDLE),("he",wt.HANDLE)]
class PI(ctypes.Structure): _fields_=[("hp",wt.HANDLE),("ht",wt.HANDLE),("pid",wt.DWORD),("tid",wt.DWORD)]
def setup():
    k32.GetCurrentProcess.restype=ctypes.c_void_p
    adv.OpenProcessToken.argtypes=[ctypes.c_void_p,wt.DWORD,ctypes.POINTER(ctypes.c_void_p)]
    adv.LookupPrivilegeValueW.argtypes=[wt.LPCWSTR,wt.LPCWSTR,ctypes.POINTER(LUID)]
    adv.AdjustTokenPrivileges.argtypes=[ctypes.c_void_p,wt.BOOL,ctypes.POINTER(TP),wt.DWORD,ctypes.c_void_p,ctypes.POINTER(wt.DWORD)]
    h=ctypes.c_void_p(); adv.OpenProcessToken(k32.GetCurrentProcess(),0x28,ctypes.byref(h))
    lu=LUID(); adv.LookupPrivilegeValueW(None,"SeDebugPrivilege",ctypes.byref(lu))
    tp=TP(); tp.n=1; tp.p[0].Luid=lu; tp.p[0].Attr=2
    adv.AdjustTokenPrivileges(h,False,ctypes.byref(tp),0,None,None)
    k32.CreateProcessW.restype=wt.BOOL
    k32.CreateProcessW.argtypes=[wt.LPCWSTR,wt.LPWSTR,ctypes.c_void_p,ctypes.c_void_p,wt.BOOL,wt.DWORD,ctypes.c_void_p,wt.LPCWSTR,ctypes.POINTER(SI),ctypes.POINTER(PI)]
    k32.OpenProcess.restype=wt.HANDLE; k32.OpenProcess.argtypes=[wt.DWORD,wt.BOOL,wt.DWORD]
    k32.ReadProcessMemory.restype=wt.BOOL
    k32.ReadProcessMemory.argtypes=[wt.HANDLE,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)]
    k32.ResumeThread.argtypes=[wt.HANDLE]; k32.TerminateProcess.argtypes=[wt.HANDLE,wt.UINT]
def rd(h,va,n):
    b=ctypes.create_string_buffer(n); g=ctypes.c_size_t(0)
    ok=k32.ReadProcessMemory(h,ctypes.c_void_p(va),b,n,ctypes.byref(g))
    return b.raw[:g.value] if (ok and g.value) else None
def rdstr(h,va,n=80):
    b=rd(h,va,n)
    if not b: return None
    z=b.find(b"\x00")
    return b[:z].decode("latin1","replace") if z and z>0 else None

OUT=sys.argv[1]; SECS=float(sys.argv[2]) if len(sys.argv)>2 else 120.0
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.abspath(os.path.join(HERE,"..",".."))
SB=os.path.join(ROOT,"run_codol_001","sandbox_ifs1_20260923")
os.makedirs(OUT,exist_ok=True)
reqlog=open(os.path.join(OUT,"http_requests.jsonl"),"w",encoding="utf-8")
reqlock=threading.Lock()

RESP = b'<?xml version="1.0" encoding="UTF-8"?><TssQosPkg><stHead><wLength>0</wLength><wCommand>0</wCommand><wVersion>1</wVersion></stHead><stBody/></TssQosPkg>'

class H(BaseHTTPRequestHandler):
    def _h(self,meth):
        ln=int(self.headers.get("Content-Length") or 0)
        body=self.rfile.read(ln) if ln>0 else b""
        rec={"t":round(time.time()-T0,2),"port":self.server.server_port,"method":meth,"path":self.path,
             "headers":{k:v for k,v in self.headers.items()},"body_len":len(body),
             "body_hex":body[:256].hex()}
        with reqlock:
            reqlog.write(json.dumps(rec,ensure_ascii=False)+"\n"); reqlog.flush()
        self.send_response(200)
        self.send_header("Content-Type","text/xml")
        self.send_header("Content-Length",str(len(RESP)))
        self.end_headers()
        if meth!="HEAD": self.wfile.write(RESP)
    def do_GET(self): self._h("GET")
    def do_POST(self): self._h("POST")
    def do_HEAD(self): self._h("HEAD")
    def log_message(self,*a): pass

def serve(port):
    try:
        s=ThreadingHTTPServer(("127.0.0.1",port),H); s.server_port=port
        threading.Thread(target=s.serve_forever,daemon=True).start()
        return s
    except Exception as e:
        print("bind %d fail: %r"%(port,e),flush=True); return None

T0=time.time()
setup()
srv=[]
for p in (8080,8081):
    s=serve(p)
    if s: srv.append(s); print("listening 127.0.0.1:%d"%p,flush=True)

si=SI(); si.cb=ctypes.sizeof(si); pi=PI()
EXE=os.path.join(SB,"codoMP_client_shipRetail.exe"); cmd='"%s" -q'%EXE
buf=ctypes.create_unicode_buffer(cmd)
ok=k32.CreateProcessW(EXE,buf,None,None,True,4,None,SB,ctypes.byref(si),ctypes.byref(pi))
print("create ok=%s pid=%d"%(bool(ok),pi.pid),flush=True)
h=k32.OpenProcess(0x0400|0x0010,False,pi.pid); print("handle=%s"%h,flush=True)
k32.ResumeThread(pi.ht)

lg=open(os.path.join(OUT,"state.jsonl"),"w",encoding="utf-8")
while time.time()-T0 < SECS:
    el=round(time.time()-T0,2)
    def u32(va):
        b=rd(h,va,4); return struct.unpack("I",b)[0] if b and len(b)==4 else None
    cur=u32(0xE4EA3C)
    rec={"t":el,"state":u32(0x84ABA50),"cur":cur,"cur_name":rdstr(h,cur,64) if cur else None,
         "res":u32(0x84ABA78),"objA":u32(0x84ABA70)}
    lg.write(json.dumps(rec,ensure_ascii=False)+"\n"); lg.flush()
    time.sleep(0.5)
lg.close(); reqlog.close()
k32.TerminateProcess(pi.hp,0)
for s in srv: s.shutdown()
print("done",flush=True)
