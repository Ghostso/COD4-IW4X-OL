"""B: poke gate [0x849B61F]=1 (dwLobby master enable) and watch the state machine."""
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
    k32.WriteProcessMemory.restype=wt.BOOL
    k32.WriteProcessMemory.argtypes=[wt.HANDLE,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)]
    k32.VirtualProtectEx.restype=wt.BOOL
    k32.VirtualProtectEx.argtypes=[wt.HANDLE,ctypes.c_void_p,ctypes.c_size_t,wt.DWORD,ctypes.POINTER(wt.DWORD)]
    k32.ResumeThread.argtypes=[wt.HANDLE]; k32.TerminateProcess.argtypes=[wt.HANDLE,wt.UINT]
def rd(h,va,n):
    b=ctypes.create_string_buffer(n); g=ctypes.c_size_t(0)
    ok=k32.ReadProcessMemory(h,ctypes.c_void_p(va),b,n,ctypes.byref(g))
    return b.raw[:g.value] if (ok and g.value) else None
def u32(h,va):
    b=rd(h,va,4); return struct.unpack("I",b)[0] if b and len(b)==4 else None
def u8(h,va):
    b=rd(h,va,1); return b[0] if b else None
def rdf(h,va,n=48):
    b=rd(h,va,n)
    if not b: return None
    z=b.find(b"\x00")
    return b[:z].decode("latin1","replace") if z and z>0 else None
def wrb(h,va,val):
    old=wt.DWORD()
    if not k32.VirtualProtectEx(h,ctypes.c_void_p(va),1,0x40,ctypes.byref(old)): return False
    w=ctypes.c_size_t(0); d=bytes([val])
    ok=k32.WriteProcessMemory(h,ctypes.c_void_p(va),d,1,ctypes.byref(w))
    k32.VirtualProtectEx(h,ctypes.c_void_p(va),1,old.value,ctypes.byref(old))
    return bool(ok)
OUT=sys.argv[1]; SECS=float(sys.argv[2]) if len(sys.argv)>2 else 120.0
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.abspath(os.path.join(HERE,"..",".."))
SB=os.path.join(ROOT,"run_codol_001","sandbox_ifs1_20260923"); os.makedirs(OUT,exist_ok=True)
setup()
si=SI(); si.cb=ctypes.sizeof(si); pi=PI()
EXE=os.path.join(SB,"codoMP_client_shipRetail.exe"); cmd='"%s" -q'%EXE
buf=ctypes.create_unicode_buffer(cmd)
ok=k32.CreateProcessW(EXE,buf,None,None,True,4,None,SB,ctypes.byref(si),ctypes.byref(pi))
h=k32.OpenProcess(0x0020|0x0008|0x0010|0x0400,False,pi.pid)
print("GAME_PID=%d h=%s"%(pi.pid,h),flush=True)
k32.ResumeThread(pi.ht)
lg=open(os.path.join(OUT,"gate.jsonl"),"w",encoding="utf-8")
t0=time.time(); poked=False; last=""
while time.time()-t0<SECS:
    el=round(time.time()-t0,2)
    if not poked and el>18:
        poked=True
        # 连续写几次（防止被清）
        for k in range(5):
            r=wrb(h,0x849B61F,1)
            print("POKE gate61F=1 -> %s"%r,flush=True); time.sleep(0.5)
        # 同时填 host 槽（之前证明需要的）
        def wrbN(va, data):
            oldp=wt.DWORD()
            if not k32.VirtualProtectEx(h,ctypes.c_void_p(va),len(data),0x40,ctypes.byref(oldp)): return False
            w=ctypes.c_size_t(0)
            ok=k32.WriteProcessMemory(h,ctypes.c_void_p(va),data,len(data),ctypes.byref(w))
            k32.VirtualProtectEx(h,ctypes.c_void_p(va),len(data),oldp.value,ctypes.byref(oldp))
            return bool(ok)
        for va in (0x81A76A8,0x81A7F34,0x81A9784):
            print("  poke host 0x%08X -> %s"%(va, wrbN(va, b"tqos.gamesafe.qq.com\x00")),flush=True)
        for va in (0x81A9780,0xE513D4):
            print("  poke port 0x%08X -> %s"%(va, wrbN(va, struct.pack("<H",8081)+b"\x00\x00")),flush=True)
        print("INJECTED at t=%.1f"%el,flush=True)
    cur=u32(h,0xE4EA3C)
    rec={"t":el,"gate":u8(h,0x849B61F),"state":u32(h,0x84ABA50),"step":u32(h,0x849BA30),
         "startcnt":u32(h,0x84ABA48),"res":u32(h,0x84ABA78),"objA":u32(h,0x84ABA70),
         "cur_s":rdf(h,cur,48) if cur else None}
    key=json.dumps({k:rec[k] for k in ("gate","state","step","startcnt","res","objA","cur_s")},sort_keys=True)
    if key!=last:
        lg.write(json.dumps(rec,ensure_ascii=False)+"\n"); lg.flush()
        print(json.dumps(rec,ensure_ascii=False),flush=True)
        last=key
    time.sleep(0.2)
lg.close(); print("done(keeping alive)",flush=True)
