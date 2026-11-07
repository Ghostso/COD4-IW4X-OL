"""Read config object vtable and try calling/inspecting around key-id lookups.
Also scan the process for the raw config string of the form host:port;..."""
import ctypes, ctypes.wintypes as wt, json, os, re, struct, sys, time
k32=ctypes.WinDLL("kernel32",use_last_error=True); adv=ctypes.WinDLL("advapi32",use_last_error=True)
class LUID(ctypes.Structure): _fields_=[("L",wt.DWORD),("H",wt.LONG)]
class LAA(ctypes.Structure): _fields_=[("Luid",LUID),("Attr",wt.DWORD)]
class TP(ctypes.Structure): _fields_=[("n",wt.DWORD),("p",LAA*1)]
class SI(ctypes.Structure):
    _fields_=[("cb",wt.DWORD),("r",wt.LPWSTR),("d",wt.LPWSTR),("t",wt.LPWSTR),("x",wt.DWORD),("y",wt.DWORD),
              ("xs",wt.DWORD),("ys",wt.DWORD),("xc",wt.DWORD),("yc",wt.DWORD),("fa",wt.DWORD),("fl",wt.DWORD),
              ("sw",wt.WORD),("cr",wt.WORD),("rp",ctypes.c_void_p),("hi",wt.HANDLE),("ho",wt.HANDLE),("he",wt.HANDLE)]
class PI(ctypes.Structure): _fields_=[("hp",wt.HANDLE),("ht",wt.HANDLE),("pid",wt.DWORD),("tid",wt.DWORD)]
class MBI(ctypes.Structure):
    _fields_=[("BaseAddress",ctypes.c_void_p),("AllocationBase",ctypes.c_void_p),("AllocationProtect",wt.DWORD),
              ("RegionSize",ctypes.c_size_t),("State",wt.DWORD),("Protect",wt.DWORD),("Type",wt.DWORD)]
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
def rd(h,va,n):
    b=ctypes.create_string_buffer(n); g=ctypes.c_size_t(0)
    ok=k32.ReadProcessMemory(h,ctypes.c_void_p(va),b,n,ctypes.byref(g))
    return b.raw[:g.value] if (ok and g.value) else None
OUT=sys.argv[1]; SECS=float(sys.argv[2]) if len(sys.argv)>2 else 45.0
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.abspath(os.path.join(HERE,"..",".."))
SB=os.path.join(ROOT,"run_codol_001","sandbox_ifs1_20260923"); os.makedirs(OUT,exist_ok=True)
setup()
si=SI(); si.cb=ctypes.sizeof(si); pi=PI()
EXE=os.path.join(SB,"codoMP_client_shipRetail.exe"); cmd='"%s" -q'%EXE
buf=ctypes.create_unicode_buffer(cmd)
ok=k32.CreateProcessW(EXE,buf,None,None,True,4,None,SB,ctypes.byref(si),ctypes.byref(pi))
h=k32.OpenProcess(0x0400|0x0010,False,pi.pid); print("pid=%d"%pi.pid,flush=True)
k32.ResumeThread(pi.ht)
pat=re.compile(rb"[A-Za-z0-9._-]{4,60}:\d{2,5}(;[A-Za-z0-9._-]{4,60}:\d{2,5})+")
t0=time.time(); scanned=False
while time.time()-t0<SECS:
    el=time.time()-t0
    if not scanned and el>20:
        scanned=True
        print("scanning...",flush=True)
        addr=0x400000; found=[]
        mbi=MBI(); last=0
        while addr<0x7FFFFFFF:
            if not k32.VirtualQueryEx(h,ctypes.c_void_p(addr),ctypes.byref(mbi),ctypes.sizeof(mbi)): break
            base=int(mbi.BaseAddress or 0); size=int(mbi.RegionSize or 0)
            if size<=0: break
            if int(mbi.State)==0x1000 and (int(mbi.Protect) & 0xEE) and size<0x4000000:
                data=rd(h,base,min(size,0x4000000))
                if data:
                    for m in pat.finditer(data):
                        s=m.group().decode("latin1")
                        if not any(x in s for x in ("chatgpt","nvidia","microsoft")): found.append((base+m.start(), s))
            addr=base+size
            if time.time()-t0>SECS-8: break
        print("candidates: %d"%len(found),flush=True)
        for va,s in found[:60]:
            print("   0x%08X  %r"%(va,s),flush=True)
        # also dump host1..host6 slots
        print("--- dwLobby cfg slots ---",flush=True)
        for nm,va in [("0x81A76A8",0x81A76A8),("0xE51184",0xE51184),("0x81A7F34",0x81A7F34),("0x81A9784",0x81A9784),("0xE513D4",0xE513D4),("0x81A9780",0x81A9780)]:
            b=rd(h,va,96)
            z=b.find(b"\x00") if b else -1
            print("   %s = %r"%(nm, b[:z].decode("latin1","replace") if b and z>0 else b[:24].hex() if b else None),flush=True)
        break
    time.sleep(0.4)
k32.TerminateProcess(pi.hp,0); print("done",flush=True)
