"""Runtime state probe v2 - modeled on the working minimal probe."""
import ctypes, ctypes.wintypes as wt, json, os, struct, sys, time

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
adv = ctypes.WinDLL("advapi32", use_last_error=True)

class LUID(ctypes.Structure): _fields_=[("L",wt.DWORD),("H",wt.LONG)]
class LAA(ctypes.Structure): _fields_=[("Luid",LUID),("Attr",wt.DWORD)]
class TP(ctypes.Structure): _fields_=[("n",wt.DWORD),("p",LAA*1)]
class SI(ctypes.Structure):
    _fields_=[("cb",wt.DWORD),("r",wt.LPWSTR),("d",wt.LPWSTR),("t",wt.LPWSTR),
              ("x",wt.DWORD),("y",wt.DWORD),("xs",wt.DWORD),("ys",wt.DWORD),
              ("xc",wt.DWORD),("yc",wt.DWORD),("fa",wt.DWORD),("fl",wt.DWORD),
              ("sw",wt.WORD),("cr",wt.WORD),("rp",ctypes.c_void_p),
              ("hi",wt.HANDLE),("ho",wt.HANDLE),("he",wt.HANDLE)]
class PI(ctypes.Structure):
    _fields_=[("hp",wt.HANDLE),("ht",wt.HANDLE),("pid",wt.DWORD),("tid",wt.DWORD)]

def setup():
    k32.GetCurrentProcess.restype=ctypes.c_void_p
    adv.OpenProcessToken.argtypes=[ctypes.c_void_p,wt.DWORD,ctypes.POINTER(ctypes.c_void_p)]
    adv.LookupPrivilegeValueW.argtypes=[wt.LPCWSTR,wt.LPCWSTR,ctypes.POINTER(LUID)]
    adv.AdjustTokenPrivileges.argtypes=[ctypes.c_void_p,wt.BOOL,ctypes.POINTER(TP),wt.DWORD,ctypes.c_void_p,ctypes.POINTER(wt.DWORD)]
    h=ctypes.c_void_p()
    adv.OpenProcessToken(k32.GetCurrentProcess(),0x28,ctypes.byref(h))
    lu=LUID(); adv.LookupPrivilegeValueW(None,"SeDebugPrivilege",ctypes.byref(lu))
    tp=TP(); tp.n=1; tp.p[0].Luid=lu; tp.p[0].Attr=2
    adv.AdjustTokenPrivileges(h,False,ctypes.byref(tp),0,None,None)
    k32.CreateProcessW.restype=wt.BOOL
    k32.CreateProcessW.argtypes=[wt.LPCWSTR,wt.LPWSTR,ctypes.c_void_p,ctypes.c_void_p,wt.BOOL,wt.DWORD,ctypes.c_void_p,wt.LPCWSTR,ctypes.POINTER(SI),ctypes.POINTER(PI)]
    k32.OpenProcess.restype=wt.HANDLE
    k32.OpenProcess.argtypes=[wt.DWORD,wt.BOOL,wt.DWORD]
    k32.ReadProcessMemory.restype=wt.BOOL
    k32.ReadProcessMemory.argtypes=[wt.HANDLE,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)]
    k32.VirtualQueryEx.restype=ctypes.c_size_t
    k32.VirtualQueryEx.argtypes=[wt.HANDLE,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t]
    k32.ResumeThread.argtypes=[wt.HANDLE]
    k32.TerminateProcess.argtypes=[wt.HANDLE,wt.UINT]

def rd(h, va, n):
    b=ctypes.create_string_buffer(n); got=ctypes.c_size_t(0)
    ok=k32.ReadProcessMemory(h, ctypes.c_void_p(va), b, n, ctypes.byref(got))
    if not ok or got.value==0: return None
    return b.raw[:got.value]

WATCH=[(0x849BA34,"I","dwLobby_state"),(0x849BA30,"I","state_prev"),(0x849BA38,"I","t1"),
       (0x849B5CC,"I","u5CC"),(0x849B8AC,"I","u8AC"),(0x84ABA50,"I","uA50"),
       (0xE4EA3C,"I","chk_arg"),(0x82CCDC2,"B","flag_dc2"),(0x849B61F,"B","flag_61f"),
       (0x849B874,"I","ptr_874")]

def main():
    out=sys.argv[1]; secs=float(sys.argv[2]) if len(sys.argv)>2 else 120.0
    step=float(sys.argv[3]) if len(sys.argv)>3 else 0.5
    HERE=os.path.dirname(os.path.abspath(__file__))
    ROOT=os.path.abspath(os.path.join(HERE,"..",".."))
    GD=os.path.join(ROOT,"run_codol_001","sandbox_ifs1_20260923")
    EXE=os.path.join(GD,"codoMP_client_shipRetail.exe")
    os.makedirs(out,exist_ok=True)
    lg=open(os.path.join(out,"state.jsonl"),"w",encoding="utf-8")
    def ev(o):
        lg.write(json.dumps(o,ensure_ascii=False)+"\n"); lg.flush()
    setup()
    ev({"ev":"setup_ok"})
    si=SI(); si.cb=ctypes.sizeof(si); pi=PI()
    cmd='"%s" -q --disable-gpu --disable-gpu-compositing'%EXE
    buf=ctypes.create_unicode_buffer(cmd)
    ok=k32.CreateProcessW(EXE,buf,None,None,True,4,None,GD,ctypes.byref(si),ctypes.byref(pi))
    ev({"ev":"create","ok":bool(ok),"pid":pi.pid,"err":ctypes.get_last_error()})
    if not ok: return
    h=k32.OpenProcess(0x0400|0x0010,False,pi.pid)
    ev({"ev":"handle","h":h,"err":ctypes.get_last_error()})
    if not h: return
    k32.ResumeThread(pi.ht)
    ev({"ev":"resumed"})
    t0=time.time()
    while time.time()-t0 < secs:
        el=round(time.time()-t0,2)
        rec={"t":el}
        for va,fmt,name in WATCH:
            b=rd(h,va,struct.calcsize(fmt))
            rec[name]= (struct.unpack(fmt,b)[0] if b and len(b)==struct.calcsize(fmt) else None)
        code=rd(h,0x7EF210,16)
        rec["code_7EF210"]=code.hex() if code else None
        ev(rec)
        time.sleep(step)
    ev({"ev":"done"})
    lg.close()
    k32.TerminateProcess(pi.hp,0)

if __name__=="__main__": main()
