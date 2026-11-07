"""Runtime state probe for CODOL: suspend-create + pre-arm handle (beats ACE),
then continuously sample game state (globals, modules, code sites) read-only.

Usage: python -X utf8 _dyn_game.py <OUTDIR> [SECONDS] [STEP]
"""
import ctypes, ctypes.wintypes as wt, json, os, struct, sys, time

k32 = ctypes.windll.kernel32
psapi = ctypes.windll.psapi

# --- proper 64-bit prototypes (missing these truncates handles) ---
k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]
k32.ResumeThread.argtypes = [wt.HANDLE]
k32.TerminateProcess.argtypes = [wt.HANDLE, wt.UINT]
k32.CloseHandle.argtypes = [wt.HANDLE]
psapi.EnumProcessModules.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD)]
psapi.EnumProcessModules.restype = wt.BOOL
psapi.GetModuleFileNameExW.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.LPWSTR, wt.DWORD]
psapi.GetModuleFileNameExW.restype = wt.DWORD

CREATE_SUSPENDED = 0x4
PROCESS_ALL_ACCESS = 0x1F0FFF
SE_DEBUG_NAME = 'SeDebugPrivilege'
TOKEN_ADJUST_PRIVILEGES = 0x20
TOKEN_QUERY = 0x8
SE_PRIVILEGE_ENABLED = 0x2

class LUID(ctypes.Structure):
    _fields_=[("LowPart",wt.DWORD),("HighPart",wt.LONG)]
class LAA(ctypes.Structure):
    _fields_=[("Luid",LUID),("Attributes",wt.DWORD)]
class TP(ctypes.Structure):
    _fields_=[("PrivilegeCount",wt.DWORD),("Privileges",LAA*1)]

def enable_debug():
    adv=ctypes.WinDLL('advapi32', use_last_error=True)
    k32.GetCurrentProcess.restype = ctypes.c_void_p
    adv.OpenProcessToken.argtypes = [ctypes.c_void_p, wt.DWORD, ctypes.POINTER(ctypes.c_void_p)]
    adv.OpenProcessToken.restype = wt.BOOL
    adv.LookupPrivilegeValueW.argtypes = [wt.LPCWSTR, wt.LPCWSTR, ctypes.POINTER(LUID)]
    adv.LookupPrivilegeValueW.restype = wt.BOOL
    adv.AdjustTokenPrivileges.argtypes = [ctypes.c_void_p, wt.BOOL, ctypes.POINTER(TP), wt.DWORD, ctypes.c_void_p, ctypes.POINTER(wt.DWORD)]
    adv.AdjustTokenPrivileges.restype = wt.BOOL
    h = ctypes.c_void_p()
    if not adv.OpenProcessToken(k32.GetCurrentProcess(), TOKEN_ADJUST_PRIVILEGES|TOKEN_QUERY, ctypes.byref(h)):
        return False, ctypes.get_last_error()
    luid=LUID()
    adv.LookupPrivilegeValueW(None, SE_DEBUG_NAME, ctypes.byref(luid))
    tp=TP(); tp.PrivilegeCount=1; tp.Privileges[0].Luid=luid; tp.Privileges[0].Attributes=SE_PRIVILEGE_ENABLED
    r=adv.AdjustTokenPrivileges(h, False, ctypes.byref(tp), 0, None, None)
    err=ctypes.get_last_error()
    k32.CloseHandle(h)
    return bool(r), err

class STARTUPINFOW(ctypes.Structure):
    _fields_=[("cb",wt.DWORD),("lpReserved",wt.LPWSTR),("lpDesktop",wt.LPWSTR),("lpTitle",wt.LPWSTR),
              ("dwX",wt.DWORD),("dwY",wt.DWORD),("dwXSize",wt.DWORD),("dwYSize",wt.DWORD),
              ("dwXCountChars",wt.DWORD),("dwYCountChars",wt.DWORD),("dwFillAttribute",wt.DWORD),
              ("dwFlags",wt.DWORD),("wShowWindow",wt.WORD),("cbReserved2",wt.WORD),
              ("lpReserved2",ctypes.POINTER(ctypes.c_byte)),("hStdInput",wt.HANDLE),
              ("hStdOutput",wt.HANDLE),("hStdError",wt.HANDLE)]
class PROCESS_INFORMATION(ctypes.Structure):
    _fields_=[("hProcess",wt.HANDLE),("hThread",wt.HANDLE),("dwProcessId",wt.DWORD),("dwThreadId",wt.DWORD)]

k32.CreateProcessW.restype = wt.BOOL
k32.CreateProcessW.argtypes = [wt.LPCWSTR, wt.LPWSTR, ctypes.c_void_p, ctypes.c_void_p,
                               wt.BOOL, wt.DWORD, ctypes.c_void_p, wt.LPCWSTR,
                               ctypes.POINTER(STARTUPINFOW), ctypes.POINTER(PROCESS_INFORMATION)]

MEM_COMMIT=0x1000
class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_=[("BaseAddress",ctypes.c_void_p),("AllocationBase",ctypes.c_void_p),
              ("AllocationProtect",wt.DWORD),("RegionSize",ctypes.c_size_t),
              ("State",wt.DWORD),("Protect",wt.DWORD),("Type",wt.DWORD)]

def rd(h, va, n):
    buf=ctypes.create_string_buffer(n); got=ctypes.c_size_t(0)
    ok=k32.ReadProcessMemory(h, ctypes.c_void_p(va), buf, n, ctypes.byref(got))
    if not ok or got.value==0: return None
    return buf.raw[:got.value]

def rd_typed(h, va, fmt):
    sz=struct.calcsize(fmt)
    b=rd(h, va, sz)
    if b is None or len(b)<sz: return None
    return struct.unpack(fmt, b)

def regions(h, lo, hi):
    out=[]; addr=lo; mbi=MEMORY_BASIC_INFORMATION()
    while addr<hi:
        if not k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)): break
        base=int(mbi.BaseAddress or 0); size=int(mbi.RegionSize or 0)
        if size<=0: break
        b0=max(base,lo); b1=min(base+size,hi)
        if b1>b0: out.append({"base":b0,"size":b1-b0,"state":int(mbi.State),"protect":int(mbi.Protect),"type":int(mbi.Type)})
        addr=base+size
    return out

def read_span(h, lo, hi, regs):
    buf=bytearray(hi-lo); fails=0
    for r in regs:
        if r["state"]!=MEM_COMMIT: continue
        b=r["base"]; remain=r["size"]
        while remain>0:
            chunk=min(remain, 0x10000)
            data=rd(h, b, chunk)
            if data is None or len(data)==0:
                fails+=1; b+=chunk; remain-=chunk; continue
            buf[b-lo:b-lo+len(data)]=data
            b+=len(data); remain-=len(data)
    return buf, fails

def modules(h):
    # with a pre-arm ALL_ACCESS handle EnumProcessModules usually works
    arr=(ctypes.c_void_p*1024)(); need=wt.DWORD(0)
    if not psapi.EnumProcessModules(h, ctypes.byref(arr), ctypes.sizeof(arr), ctypes.byref(need)):
        return None, ctypes.get_last_error()
    n=min(need.value//ctypes.sizeof(ctypes.c_void_p), 1024)
    out=[]
    for i in range(n):
        base=int(arr[i] or 0)
        buf=ctypes.create_unicode_buffer(1024)
        if psapi.GetModuleFileNameExW(h, ctypes.c_void_p(base), buf, 1024):
            out.append({"base":base,"name":buf.value})
    return out, 0

# ---- watch list (game exe, base 0x400000) ----
WATCH = [
    (0x849BA34,"u32","dwLobby_state"),
    (0x849BA30,"u32","dwLobby_state_prev"),
    (0x849BA38,"u32","dwLobby_t1"),
    (0x849B5CC,"u32","u_849B5CC"),
    (0x849B8AC,"u32","u_849B8AC"),
    (0x84ABA50,"u32","u_84ABA50"),
    (0xE4EA3C,"u32","chk_arg"),
    (0x81AA118,"u32","t_a"),
    (0x81AA110,"u32","t_b"),
    (0x81AA114,"u32","t_c"),
    (0x82CCDC2,"u8","flag_82CCDC2"),
    (0x849B61F,"u8","flag_849B61F"),
    (0x849B874,"u32","ptr_849B874"),
]

def main():
    out = sys.argv[1]
    secs = float(sys.argv[2]) if len(sys.argv)>2 else 120.0
    step = float(sys.argv[3]) if len(sys.argv)>3 else 0.5
    HERE=os.path.dirname(os.path.abspath(__file__))
    ROOT=os.path.abspath(os.path.join(HERE,"..",".."))
    EXE=os.path.join(ROOT,"run_codol_001","sandbox_ifs1_20260923","codoMP_client_shipRetail.exe")
    CWD=os.path.join(ROOT,"run_codol_001","sandbox_ifs1_20260923")
    os.makedirs(out, exist_ok=True)

    ok,err = enable_debug()
    print("SeDebugPrivilege=%s err=%d"%(ok,err), flush=True)

    si=STARTUPINFOW(); si.cb=ctypes.sizeof(si)
    pi=PROCESS_INFORMATION()
    cmd='"%s" -q --disable-gpu --disable-gpu-compositing'%EXE
    buf=ctypes.create_unicode_buffer(cmd)
    if not k32.CreateProcessW(EXE, buf, None, None, True, CREATE_SUSPENDED, None, CWD, ctypes.byref(si), ctypes.byref(pi)):
        raise SystemExit("CreateProcess failed err=%d"%ctypes.get_last_error())
    pid=pi.dwProcessId
    print("created suspended pid=%d"%pid, flush=True)

    h=k32.OpenProcess(0x0400|0x0010, False, pid)
    print("pre-arm OpenProcess(ALL_ACCESS) -> %s err=%d"%(h, ctypes.get_last_error()), flush=True)
    if not h:
        k32.TerminateProcess(pi.hProcess,1); raise SystemExit("no handle")

    k32.ResumeThread(pi.hThread)
    print("resumed", flush=True)

    log=open(os.path.join(out,"state.jsonl"),"w",encoding="utf-8")
    def ev(o):
        log.write(json.dumps(o,ensure_ascii=False)+"\n"); log.flush()

    t0=time.time()
    mods=None
    while time.time()-t0 < secs:
        el=time.time()-t0
        rec={"t":round(el,2)}
        for va,fmt,name in WATCH:
            v=rd_typed(h,va,fmt)
            rec[name]= (v[0] if v else None)
        # code site check
        cb_=rd(h,0x7EF210,16)
        rec["code_7EF210"]= cb_.hex() if cb_ else None
        if mods is None and el>6:
            m,e=modules(h)
            if m is not None:
                mods=m
                json.dump(m, open(os.path.join(out,"modules.json"),"w"), indent=1)
                ev({"ev":"modules","count":len(m),"err":e})
            else:
                ev({"ev":"modules_fail","err":e})
        ev(rec)
        time.sleep(step)

    ev({"ev":"done"})
    log.close()
    try:
        k32.TerminateProcess(pi.hProcess,0)
    except Exception: pass
    print("done", flush=True)

if __name__=="__main__":
    main()
