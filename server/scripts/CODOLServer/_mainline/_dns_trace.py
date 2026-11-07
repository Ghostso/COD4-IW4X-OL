"""ETW DNS trace + game launch + state sample. Elevated."""
import ctypes, ctypes.wintypes as wt, json, os, subprocess, sys, time, struct

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
    h=ctypes.c_void_p(); adv.OpenProcessToken(k32.GetCurrentProcess(),0x28,ctypes.byref(h))
    lu=LUID(); adv.LookupPrivilegeValueW(None,"SeDebugPrivilege",ctypes.byref(lu))
    tp=TP(); tp.n=1; tp.p[0].Luid=lu; tp.p[0].Attr=2
    adv.AdjustTokenPrivileges(h,False,ctypes.byref(tp),0,None,None)
    k32.CreateProcessW.restype=wt.BOOL
    k32.CreateProcessW.argtypes=[wt.LPCWSTR,wt.LPWSTR,ctypes.c_void_p,ctypes.c_void_p,wt.BOOL,wt.DWORD,ctypes.c_void_p,wt.LPCWSTR,ctypes.POINTER(SI),ctypes.POINTER(PI)]
    k32.OpenProcess.restype=wt.HANDLE; k32.OpenProcess.argtypes=[wt.DWORD,wt.BOOL,wt.DWORD]
    k32.ReadProcessMemory.restype=wt.BOOL
    k32.ReadProcessMemory.argtypes=[wt.HANDLE,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)]
    k32.VirtualQueryEx.restype=ctypes.c_size_t
    k32.VirtualQueryEx.argtypes=[wt.HANDLE,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t]
    k32.ResumeThread.argtypes=[wt.HANDLE]; k32.TerminateProcess.argtypes=[wt.HANDLE,wt.UINT]
    k32.WaitForSingleObject.argtypes=[wt.HANDLE,wt.DWORD]

def rd(h,va,n):
    b=ctypes.create_string_buffer(n); got=ctypes.c_size_t(0)
    ok=k32.ReadProcessMemory(h,ctypes.c_void_p(va),b,n,ctypes.byref(got))
    return b.raw[:got.value] if (ok and got.value) else None

def run(cmd):
    r=subprocess.run(cmd, capture_output=True)
    return (r.stdout or b'').decode('gbk','replace')+(r.stderr or b'').decode('gbk','replace')

def main():
    out=sys.argv[1]; secs=float(sys.argv[2]) if len(sys.argv)>2 else 110.0
    HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.abspath(os.path.join(HERE,"..",".."))
    GD=os.path.join(ROOT,"run_codol_001","sandbox_ifs1_20260923")
    os.makedirs(out,exist_ok=True)
    log=open(os.path.join(out,"dns_etl.txt"),"w",encoding="utf-8")
    def say(s): log.write(s+"\n"); log.flush(); print(s,flush=True)
    setup()
    etl=os.path.join(out,"dns.etl")
    # start DNS ETW trace
    say(run(['logman','start','codoldns','-p','Microsoft-Windows-DNS-Client','-o',etl,'-ets']))
    try:
        # launch game (suspend + handle)
        si=SI(); si.cb=ctypes.sizeof(si); pi=PI()
        EXE=os.path.join(GD,"codoMP_client_shipRetail.exe")
        cmd='"%s" -q --disable-gpu --disable-gpu-compositing'%EXE
        buf=ctypes.create_unicode_buffer(cmd)
        ok=k32.CreateProcessW(EXE,buf,None,None,True,4,None,GD,ctypes.byref(si),ctypes.byref(pi))
        say("create ok=%s pid=%d"%(bool(ok),pi.pid))
        h=k32.OpenProcess(0x0400|0x0010,False,pi.pid); say("handle=%s"%h)
        k32.ResumeThread(pi.ht)
        t0=time.time(); lg=open(os.path.join(out,"state.jsonl"),"w",encoding="utf-8")
        while time.time()-t0 < secs:
            el=round(time.time()-t0,2)
            def u32(va): 
                b=rd(h,va,4); return struct.unpack("I",b)[0] if b and len(b)==4 else None
            rec={"t":el,"st":u32(0x849BA34),"arg":u32(0xE4EA3C),"u5CC":u32(0x849B5CC)}
            lg.write(json.dumps(rec)+"\n"); lg.flush()
            time.sleep(0.5)
        lg.close()
        k32.TerminateProcess(pi.hp,0)
    finally:
        say(run(['logman','stop','codoldns','-ets']))
    log.close()

main()
