import ctypes, ctypes.wintypes as wt, os, struct, sys, time
k32 = ctypes.WinDLL("kernel32", use_last_error=True)
adv = ctypes.WinDLL("advapi32", use_last_error=True)
class LUID(ctypes.Structure): _fields_=[("L",wt.DWORD),("H",wt.LONG)]
class LAA(ctypes.Structure): _fields_=[("Luid",LUID),("Attr",wt.DWORD)]
class TP(ctypes.Structure): _fields_=[("n",wt.DWORD),("p",LAA*1)]
k32.GetCurrentProcess.restype=ctypes.c_void_p
adv.OpenProcessToken.argtypes=[ctypes.c_void_p,wt.DWORD,ctypes.POINTER(ctypes.c_void_p)]
h=ctypes.c_void_p()
adv.OpenProcessToken(k32.GetCurrentProcess(),0x28,ctypes.byref(h))
lu=LUID(); adv.LookupPrivilegeValueW(None,"SeDebugPrivilege",ctypes.byref(lu))
tp=TP(); tp.n=1; tp.p[0].Luid=lu; tp.p[0].Attr=2
adv.AdjustTokenPrivileges(h,False,ctypes.byref(tp),0,None,None)
print("SeDebug err=%d"%ctypes.get_last_error())
class SI(ctypes.Structure):
    _fields_=[("cb",wt.DWORD),("r",wt.LPWSTR),("d",wt.LPWSTR),("t",wt.LPWSTR),
              ("x",wt.DWORD),("y",wt.DWORD),("xs",wt.DWORD),("ys",wt.DWORD),
              ("xc",wt.DWORD),("yc",wt.DWORD),("fa",wt.DWORD),("fl",wt.DWORD),
              ("sw",wt.WORD),("cr",wt.WORD),("rp",ctypes.c_void_p),
              ("hi",wt.HANDLE),("ho",wt.HANDLE),("he",wt.HANDLE)]
class PI(ctypes.Structure):
    _fields_=[("hp",wt.HANDLE),("ht",wt.HANDLE),("pid",wt.DWORD),("tid",wt.DWORD)]
k32.CreateProcessW.restype=wt.BOOL
k32.CreateProcessW.argtypes=[wt.LPCWSTR,wt.LPWSTR,ctypes.c_void_p,ctypes.c_void_p,wt.BOOL,wt.DWORD,ctypes.c_void_p,wt.LPCWSTR,ctypes.POINTER(SI),ctypes.POINTER(PI)]
k32.OpenProcess.restype=wt.HANDLE
k32.OpenProcess.argtypes=[wt.DWORD,wt.BOOL,wt.DWORD]
k32.ReadProcessMemory.restype=wt.BOOL
k32.ReadProcessMemory.argtypes=[wt.HANDLE,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)]
k32.ResumeThread.argtypes=[wt.HANDLE]
ROOT=r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_ifs1_20260923"
EXE=os.path.join(ROOT,"codoMP_client_shipRetail.exe")
si=SI(); si.cb=ctypes.sizeof(si); pi=PI()
cmd='"%s" -q'%EXE
buf=ctypes.create_unicode_buffer(cmd)
ok=k32.CreateProcessW(EXE,buf,None,None,True,4,None,ROOT,ctypes.byref(si),ctypes.byref(pi))
print("CreateProcess ok=%s pid=%d err=%d"%(bool(ok),pi.pid,ctypes.get_last_error()))
h2=k32.OpenProcess(0x0400|0x0010,False,pi.pid)
print("pre-arm handle=%s err=%d"%(h2,ctypes.get_last_error()))
buf2=ctypes.create_string_buffer(4); got=ctypes.c_size_t(0)
r=k32.ReadProcessMemory(h2,ctypes.c_void_p(0x400000),buf2,4,ctypes.byref(got))
print("read(suspended) ok=%s got=%d data=%s err=%d"%(bool(r),got.value,buf2.raw[:got.value].hex(),ctypes.get_last_error()))
k32.ResumeThread(pi.ht)
time.sleep(2)
r=k32.ReadProcessMemory(h2,ctypes.c_void_p(0x400000),buf2,4,ctypes.byref(got))
print("read(t+2s) ok=%s got=%d data=%s err=%d"%(bool(r),got.value,buf2.raw[:got.value].hex(),ctypes.get_last_error()))
time.sleep(6)
r=k32.ReadProcessMemory(h2,ctypes.c_void_p(0x400000),buf2,4,ctypes.byref(got))
print("read(t+8s) ok=%s got=%d data=%s err=%d"%(bool(r),got.value,buf2.raw[:got.value].hex(),ctypes.get_last_error()))
k32.TerminateProcess(pi.hp,0)
print("DONE")
