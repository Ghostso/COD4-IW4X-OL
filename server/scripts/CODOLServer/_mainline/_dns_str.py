"""Read the runtime DNS-check string and related objects."""
import ctypes, ctypes.wintypes as wt, json, os, struct, sys, time
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
def rdstr(h,va,n=96):
    b=rd(h,va,n)
    if not b: return None
    z=b.find(b"\x00")
    return b[:z].decode("latin1","replace") if z>0 else None
out=sys.argv[1]; secs=float(sys.argv[2]) if len(sys.argv)>2 else 90.0
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.abspath(os.path.join(HERE,"..",".."))
GD=os.path.join(ROOT,"run_codol_001","sandbox_ifs1_20260923"); os.makedirs(out,exist_ok=True)
setup()
si=SI(); si.cb=ctypes.sizeof(si); pi=PI()
EXE=os.path.join(GD,"codoMP_client_shipRetail.exe"); cmd='"%s" -q'%EXE
buf=ctypes.create_unicode_buffer(cmd)
ok=k32.CreateProcessW(EXE,buf,None,None,True,4,None,GD,ctypes.byref(si),ctypes.byref(pi))
h=k32.OpenProcess(0x4000|0x0010,False,pi.pid)
print("pid=%d handle=%s"%(pi.pid,h),flush=True)
k32.ResumeThread(pi.ht)
lg=open(os.path.join(out,"dns.jsonl"),"w",encoding="utf-8")
t0=time.time(); seen=set()
while time.time()-t0<secs:
    el=round(time.time()-t0,2)
    def u32(va):
        b=rd(h,va,4); return struct.unpack("I",b)[0] if b and len(b)==4 else None
    rec={"t":el,
         "objA":u32(0x84ABA70),"objB":u32(0x84ABA74),"res":u32(0x84ABA78),
         "state":u32(0x84ABA50),"cur":u32(0xE4EA3C),
         "sa_static":rdstr(h,0x81A76A8,96),
         "sa_deref":None,"objA_field":None}
    if rec["objA"]:
        p=u32(rec["objA"])
        rec["objA_field"]=p
        if p: rec["sa_deref"]=rdstr(h,p,96)
    lg.write(json.dumps(rec,ensure_ascii=False)+"\n"); lg.flush()
    time.sleep(0.5)
lg.close(); k32.TerminateProcess(pi.hp,0)
print("done",flush=True)
