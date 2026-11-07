"""Inject a hostname into 0x81A76A8 (writable global) and see if DW_DNS_ERROR clears.
Also tries variants: poke host1, host4, host6 slots with 127.0.0.1 / 211.147.81.116."""
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
def rdf(h,va,n=64):
    b=rd(h,va,n)
    if not b: return None
    z=b.find(b"\x00")
    return b[:z].decode("latin1","replace") if z and z>0 else None
def wr(h,va,data):
    old=wt.DWORD()
    if not k32.VirtualProtectEx(h,ctypes.c_void_p(va),len(data),0x40,ctypes.byref(old)):
        return False, "protect"
    w=ctypes.c_size_t(0)
    ok=k32.WriteProcessMemory(h,ctypes.c_void_p(va),data,len(data),ctypes.byref(w))
    k32.VirtualProtectEx(h,ctypes.c_void_p(va),len(data),old.value,ctypes.byref(old))
    return bool(ok), w.value
OUT=sys.argv[1]; SECS=float(sys.argv[2]) if len(sys.argv)>2 else 120.0
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.abspath(os.path.join(HERE,"..",".."))
SB=os.path.join(ROOT,"run_codol_001","sandbox_ifs1_20260923"); os.makedirs(OUT,exist_ok=True)
setup()
si=SI(); si.cb=ctypes.sizeof(si); pi=PI()
EXE=os.path.join(SB,"codoMP_client_shipRetail.exe"); cmd='"%s" -q'%EXE
buf=ctypes.create_unicode_buffer(cmd)
ok=k32.CreateProcessW(EXE,buf,None,None,True,4,None,SB,ctypes.byref(si),ctypes.byref(pi))
h=k32.OpenProcess(0x0020|0x0008|0x0010|0x0400,False,pi.pid)   # WRITE|OPERATION|READ|QUERY
print("pid=%d h=%s"%(pi.pid,h),flush=True)
k32.ResumeThread(pi.ht)
t0=time.time(); poked=False
lg=open(os.path.join(OUT,"poke.jsonl"),"w",encoding="utf-8")
while time.time()-t0<SECS:
    el=round(time.time()-t0,2)
    if not poked and el>16:
        poked=True
        print("poking...",flush=True)
        for va,name in [(0x81A76A8,"host1"),(0x81A7F34,"host4"),(0x81A9784,"host6")]:
            for cand in (b"211.147.81.116\x00", b"127.0.0.1\x00", b"tqos.gamesafe.qq.com\x00"):
                r=wr(h,va,cand)
                print("  write %-6s 0x%08X %-22r -> %s"%(name,va,cand[:20],r),flush=True)
        for va,name in [(0x81A9780,"port5"),(0xE513D4,"port3")]:
            r=wr(h,va,struct.pack("<H",8081)+b"\x00"*2)
            print("  write %-6s 0x%08X =8081 -> %s"%(name,va,r),flush=True)
    if int(el*2)%10==0:
        rec={"t":el,"cur":u32(h,0xE4EA3C),"cur_s":rdf(h,u32(h,0xE4EA3C) or 0,48),
             "res":u32(h,0x84ABA78),"objA":u32(h,0x84ABA70),"objB":u32(h,0x84ABA74),
             "state":u32(h,0x84ABA50),"h1":rdf(h,0x81A76A8,40),"h4":rdf(h,0x81A7F34,40)}
        lg.write(json.dumps(rec,ensure_ascii=False)+"\n"); lg.flush()
    time.sleep(0.5)
lg.close(); k32.TerminateProcess(pi.hp,0); print("done",flush=True)
