"""Sampler: catch the moment [0xE4EA3C] changes and dump the surrounding state.
Also snapshot the dwLobby state machine globals and the DW state-name pointer table."""
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
def u32(h,va):
    b=rd(h,va,4)
    return struct.unpack("I",b)[0] if b and len(b)==4 else None
def rdf(h,va,n=48):
    b=rd(h,va,n)
    if not b: return None
    z=b.find(b"\x00")
    return b[:z].decode("latin1","replace") if z and z>0 else None
GLOBALS=[("state",0x84ABA50),("state_prev",0x84ABA54),("t1",0x84ABA4C),("t2",0x84ABA48),
         ("res",0x84ABA78),("objA",0x84ABA70),("objB",0x84ABA74),("err2",0x84ABA5C),
         ("cur",0xE4EA3C),("flag",0x849BA3D),("u874",0x849B874),("u8AC",0x849B8AC),("u508",0x84ABB08),("u514",0x84ABB14)]
OUT=sys.argv[1]; SECS=float(sys.argv[2]) if len(sys.argv)>2 else 110.0
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.abspath(os.path.join(HERE,"..",".."))
SB=os.path.join(ROOT,"run_codol_001","sandbox_ifs1_20260923"); os.makedirs(OUT,exist_ok=True)
setup()
si=SI(); si.cb=ctypes.sizeof(si); pi=PI()
EXE=os.path.join(SB,"codoMP_client_shipRetail.exe"); cmd='"%s" -q'%EXE
buf=ctypes.create_unicode_buffer(cmd)
ok=k32.CreateProcessW(EXE,buf,None,None,True,4,None,SB,ctypes.byref(si),ctypes.byref(pi))
h=k32.OpenProcess(0x0400|0x0010,False,pi.pid); print("pid=%d"%pi.pid,flush=True)
k32.ResumeThread(pi.ht)
lg=open(os.path.join(OUT,"globals.jsonl"),"w",encoding="utf-8")
t0=time.time(); prev={}
while time.time()-t0<SECS:
    el=round(time.time()-t0,3)
    row={"t":el}
    for name,va in GLOBALS: row[name]=u32(h,va)
    cur=row.get("cur")
    row["cur_s"]=rdf(h,cur,48) if cur else None
    # 变化即记录
    if any(row.get(n)!=prev.get(n) for n,_ in GLOBALS):
        lg.write(json.dumps(row,ensure_ascii=False)+"\n"); lg.flush()
        print(json.dumps({k:row[k] for k in ("t","state","state_prev","t1","t2","res","objA","objB","err2","cur","cur_s","flag","u874","u8AC")},ensure_ascii=False),flush=True)
        prev={n:row.get(n) for n,_ in GLOBALS}
    time.sleep(0.2)
lg.close(); k32.TerminateProcess(pi.hp,0); print("done",flush=True)
