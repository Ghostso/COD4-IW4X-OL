import ctypes
import ctypes.wintypes as wt
import datetime as dt
import os
import subprocess
import time

ROOT = os.getcwd()
COD = os.path.join(ROOT, 'COD OL')
TCLS = os.path.join(COD, 'TCLS')
CLIENT = os.path.join(TCLS, 'Client.exe')
WATCH = [TCLS, os.path.join(COD, 'TenproxyLog'), os.path.join(COD, 'Logs'), os.path.join(ROOT, 'WeGame', 'tcls'), os.path.join(ROOT, 'WeGame', 'log')]
PATTERNS = [b'TCLS_SHAREDMEMEMORY', b'StartGame', b'LaunchGame', b'RunGame', b'CreateFileMapping', b'MapViewOfFile', b'GetGameSignatrue', b'GetJumpSignatrue', b'WIN_NO_TCLS', b'OpenFileMapping']

def iso(t=None):
    return dt.datetime.fromtimestamp(time.time() if t is None else t).isoformat(timespec='milliseconds')

def out(*a):
    print(*a, flush=True)

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
ntdll = ctypes.WinDLL('ntdll', use_last_error=True)
shell32 = ctypes.WinDLL('shell32', use_last_error=True)

class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [('dwSize', wt.DWORD), ('cntUsage', wt.DWORD), ('th32ProcessID', wt.DWORD), ('th32DefaultHeapID', ctypes.c_void_p), ('th32ModuleID', wt.DWORD), ('cntThreads', wt.DWORD), ('th32ParentProcessID', wt.DWORD), ('pcPriClassBase', ctypes.c_long), ('dwFlags', wt.DWORD), ('szExeFile', wt.WCHAR * 260)]
class FILETIME(ctypes.Structure):
    _fields_ = [('dwLowDateTime', wt.DWORD), ('dwHighDateTime', wt.DWORD)]
class UNICODE_STRING(ctypes.Structure):
    _fields_ = [('Length', wt.USHORT), ('MaximumLength', wt.USHORT), ('Buffer', ctypes.c_void_p)]
class OBJECT_ATTRIBUTES(ctypes.Structure):
    _fields_ = [('Length', wt.ULONG), ('RootDirectory', wt.HANDLE), ('ObjectName', ctypes.POINTER(UNICODE_STRING)), ('Attributes', wt.ULONG), ('SecurityDescriptor', ctypes.c_void_p), ('SecurityQualityOfService', ctypes.c_void_p)]
class SHELLEXECUTEINFOW(ctypes.Structure):
    _fields_ = [('cbSize', wt.DWORD), ('fMask', wt.ULONG), ('hwnd', wt.HWND), ('lpVerb', wt.LPCWSTR), ('lpFile', wt.LPCWSTR), ('lpParameters', wt.LPCWSTR), ('lpDirectory', wt.LPCWSTR), ('nShow', ctypes.c_int), ('hInstApp', wt.HANDLE), ('lpIDList', ctypes.c_void_p), ('lpClass', wt.LPCWSTR), ('hkeyClass', wt.HANDLE), ('dwHotKey', wt.DWORD), ('hIcon', wt.HANDLE), ('hProcess', wt.HANDLE)]

k32.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]; k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
k32.Process32FirstW.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
k32.Process32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]; k32.OpenProcess.restype = wt.HANDLE
k32.QueryFullProcessImageNameW.argtypes = [wt.HANDLE, wt.DWORD, wt.LPWSTR, ctypes.POINTER(wt.DWORD)]
k32.GetProcessTimes.argtypes = [wt.HANDLE, ctypes.POINTER(FILETIME), ctypes.POINTER(FILETIME), ctypes.POINTER(FILETIME), ctypes.POINTER(FILETIME)]
k32.GetExitCodeProcess.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
k32.GetProcessId.argtypes = [wt.HANDLE]; k32.GetProcessId.restype = wt.DWORD
k32.CloseHandle.argtypes = [wt.HANDLE]
ntdll.NtOpenDirectoryObject.argtypes = [ctypes.POINTER(wt.HANDLE), wt.DWORD, ctypes.POINTER(OBJECT_ATTRIBUTES)]
ntdll.NtQueryDirectoryObject.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.ULONG, wt.BOOLEAN, wt.BOOLEAN, ctypes.POINTER(wt.ULONG), ctypes.POINTER(wt.ULONG)]
shell32.ShellExecuteExW.argtypes = [ctypes.POINTER(SHELLEXECUTEINFOW)]

def procs():
    h = k32.CreateToolhelp32Snapshot(2, 0)
    if h == ctypes.c_void_p(-1).value: return {}
    pe = PROCESSENTRY32W(); pe.dwSize = ctypes.sizeof(pe); d = {}
    try:
        ok = k32.Process32FirstW(h, ctypes.byref(pe))
        while ok:
            d[int(pe.th32ProcessID)] = (int(pe.th32ParentProcessID), pe.szExeFile)
            ok = k32.Process32NextW(h, ctypes.byref(pe))
    finally: k32.CloseHandle(h)
    return d

def details(pid):
    h = k32.OpenProcess(0x1000, False, pid); d = {}
    if not h: return d
    try:
        n = wt.DWORD(1024); b = ctypes.create_unicode_buffer(n.value)
        if k32.QueryFullProcessImageNameW(h, 0, b, ctypes.byref(n)): d['path'] = b.value
        c=FILETIME(); x=FILETIME(); k=FILETIME(); u=FILETIME()
        if k32.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(x), ctypes.byref(k), ctypes.byref(u)):
            t=(c.dwHighDateTime<<32)|c.dwLowDateTime
            if t: d['created']=(dt.datetime(1601,1,1)+dt.timedelta(microseconds=t/10)).isoformat(timespec='milliseconds')
    finally: k32.CloseHandle(h)
    return d

def relevant(name):
    n=name.upper()
    return any(x in n for x in ('TCLS','XTDL','TENPROXY','RAIL_','SHAREDMEM','TPF_SHARE'))

def ns():
    sid=wt.DWORD(); k32.ProcessIdToSessionId(k32.GetCurrentProcessId(),ctypes.byref(sid)); return r'\Sessions\%d\BaseNamedObjects'%sid.value

def enum_dir(path):
    b=ctypes.create_unicode_buffer(path); us=UNICODE_STRING(len(path)*2,(len(path)+1)*2,ctypes.cast(b,ctypes.c_void_p)); oa=OBJECT_ATTRIBUTES(ctypes.sizeof(OBJECT_ATTRIBUTES),None,ctypes.pointer(us),0,None,None); h=wt.HANDLE()
    if ntdll.NtOpenDirectoryObject(ctypes.byref(h),1,ctypes.byref(oa))<0: return []
    r=[]; buf=ctypes.create_string_buffer(65536); ctx=wt.ULONG(0); ret=wt.ULONG(0); first=True
    try:
        while True:
            st=ntdll.NtQueryDirectoryObject(h,buf,len(buf),True,first,ctypes.byref(ctx),ctypes.byref(ret)); first=False
            if st==0x8000001A or st<0: break
            base=ctypes.sizeof(UNICODE_STRING); nu=UNICODE_STRING.from_buffer_copy(buf.raw[:base]); tu=UNICODE_STRING.from_buffer_copy(buf.raw[base:base*2])
            if not nu.Length: break
            name=ctypes.wstring_at(nu.Buffer,nu.Length//2); typ=ctypes.wstring_at(tu.Buffer,tu.Length//2) if tu.Length else ''
            r.append((name,typ))
    finally: k32.CloseHandle(h)
    return r

def named():
    d={}
    for nsp in (r'\BaseNamedObjects',ns()):
        for name,typ in enum_dir(nsp):
            if relevant(name): d[(nsp,name,typ)]=time.time()
    return d

def files():
    d={}
    for root in WATCH:
        if not os.path.isdir(root): continue
        for base,_,fs in os.walk(root):
            for fn in fs:
                p=os.path.join(base,fn)
                try: st=os.stat(p); d[p]=(st.st_size,st.st_mtime_ns)
                except OSError: pass
    return d

def hits(path):
    try: data=open(path,'rb').read(4*1024*1024)
    except OSError: return []
    r=[]
    for p in PATTERNS:
        if p.lower() in data.lower(): r.append(p.decode())
        elif p.decode().encode('utf-16le').lower() in data.lower(): r.append(p.decode()+'/UTF16')
    return r

if not os.path.isfile(CLIENT): out('MISSING',CLIENT); raise SystemExit(2)
bp=procs(); bps=set(bp); bn=named(); bf=files()
out('OBSERVER_START',iso()); out('TARGET',CLIENT); out('HOT_BASELINE','PIDS',len(bps),'RELEVANT_NAMES',len(bn))
for k in sorted(bn): out('BASE_NAME',k[0],k[2],k[1])
for pid,(ppid,n) in sorted(bp.items()):
    if relevant(n): out('BASE_PROCESS',pid,ppid,n)
sei=SHELLEXECUTEINFOW(); sei.cbSize=ctypes.sizeof(sei); sei.fMask=0x40|0x100; sei.lpVerb='runas'; sei.lpFile=CLIENT; sei.lpDirectory=TCLS; sei.nShow=1
if not shell32.ShellExecuteExW(ctypes.byref(sei)) or not sei.hProcess: out('SHELLEXECUTE_FAIL',ctypes.get_last_error()); raise SystemExit(4)
root=int(k32.GetProcessId(sei.hProcess)); start=time.time(); out('CREATE_PROCESS',iso(start),'ROOT_PID',root)
first={}; last={}; det={}; nm={}; exitcode=None; nextp=start; nextn=start
while time.time()<start+65:
    now=time.time()
    if now>=nextp:
        cp=procs()
        for pid,(ppid,name) in sorted(cp.items()):
            if pid in bps: continue
            rel=relevant(name) or pid==root or ppid in set(first)
            if not rel: continue
            if pid not in first:
                first[pid]=now; det[pid]=details(pid); out('PROCESS_FIRST_SEEN',iso(now),pid,'PPID',ppid,'NAME',name,'PATH',det[pid].get('path',''),'CREATED',det[pid].get('created',''))
            last[pid]=now
        c=wt.DWORD()
        if exitcode is None and k32.GetExitCodeProcess(sei.hProcess,ctypes.byref(c)) and c.value!=259: exitcode=int(c.value); out('ROOT_EXIT',iso(now),'PID',root,'EXITCODE',exitcode)
        nextp+=0.10
    if now>=nextn:
        for k in named():
            if k not in bn:
                if k not in nm: nm[k]=now; out('NAMED_FIRST_SEEN',iso(now),'NS',k[0],'TYPE',k[2],'NAME',k[1])
                nm[k]=now
        nextn+=0.20
    time.sleep(0.03)
final=procs(); c=wt.DWORD(); k32.GetExitCodeProcess(sei.hProcess,ctypes.byref(c)); out('OBSERVE_END',iso(),'ROOT_EXITCODE',None if c.value==259 else int(c.value))
for pid in sorted(first):
    ppid,name=(final.get(pid) or bp.get(pid) or (0,''))
    out('PROCESS_SUMMARY',pid,'PPID',ppid,'NAME',name,'FIRST',iso(first[pid]),'LAST_VISIBLE',iso(last.get(pid,first[pid])),'PATH',det.get(pid,{}).get('path',''),'CREATED',det.get(pid,{}).get('created',''))
for k in sorted(nm): out('NAMED_SUMMARY',k[0],k[2],k[1],'FIRST_VISIBLE',iso(nm[k]),'LAST_VISIBLE',iso(nm[k]))
post=files(); ch=[p for p,m in post.items() if p not in bf or bf[p]!=m]
out('CHANGED_OR_NEW_FILES',len(ch))
for p in sorted(ch):
    try: out('FILE',iso(os.path.getmtime(p)),os.path.getsize(p),p,'PATTERNS',','.join(hits(p)))
    except OSError: pass
out('NO_STOP_NEEDED' if root not in final else 'ALIVE_AT_END_NO_STOP',root); k32.CloseHandle(sei.hProcess); out('OBSERVER_END',iso())
