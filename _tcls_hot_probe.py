import ctypes
import ctypes.wintypes as wt
import datetime as dt
import os
import sys
import time

ROOT = os.getcwd()
COD = os.path.join(ROOT, 'COD OL')
TCLS = os.path.join(COD, 'TCLS')
CLIENT = os.path.join(TCLS, 'Client.exe')
WATCH = [TCLS, os.path.join(COD, 'TenproxyLog'), os.path.join(COD, 'Logs'), os.path.join(ROOT, 'WeGame', 'tcls')]
PATTERNS = [b'TCLS_SHAREDMEMEMORY', b'StartGame', b'LaunchGame', b'RunGame', b'CreateFileMapping', b'MapViewOfFile', b'GetGameSignatrue', b'GetJumpSignatrue', b'WIN_NO_TCLS', b'OpenFileMapping']

def out(*a):
    print(*a, flush=True)

def iso(t=None):
    return dt.datetime.fromtimestamp(time.time() if t is None else t).isoformat(timespec='milliseconds')

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
ntdll = ctypes.WinDLL('ntdll', use_last_error=True)
shell32 = ctypes.WinDLL('shell32', use_last_error=True)

TH32CS_SNAPPROCESS = 2
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

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

class SYSTEM_HANDLE_TABLE_ENTRY_INFO_EX(ctypes.Structure):
    _fields_ = [('Object', ctypes.c_void_p), ('UniqueProcessId', ctypes.c_void_p), ('HandleValue', ctypes.c_void_p), ('GrantedAccess', wt.ULONG), ('CreatorBackTraceIndex', wt.USHORT), ('ObjectTypeIndex', wt.USHORT), ('HandleAttributes', wt.ULONG), ('Reserved', wt.ULONG)]

k32.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
k32.Process32FirstW.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
k32.Process32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.OpenProcess.restype = wt.HANDLE
k32.QueryFullProcessImageNameW.argtypes = [wt.HANDLE, wt.DWORD, wt.LPWSTR, ctypes.POINTER(wt.DWORD)]
k32.GetProcessTimes.argtypes = [wt.HANDLE, ctypes.POINTER(FILETIME), ctypes.POINTER(FILETIME), ctypes.POINTER(FILETIME), ctypes.POINTER(FILETIME)]
k32.GetExitCodeProcess.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
k32.GetProcessId.argtypes = [wt.HANDLE]
k32.GetProcessId.restype = wt.DWORD
k32.CloseHandle.argtypes = [wt.HANDLE]
k32.DuplicateHandle.argtypes = [wt.HANDLE, wt.HANDLE, wt.HANDLE, ctypes.POINTER(wt.HANDLE), wt.DWORD, wt.BOOL, wt.DWORD]
ntdll.NtOpenDirectoryObject.argtypes = [ctypes.POINTER(wt.HANDLE), wt.DWORD, ctypes.POINTER(OBJECT_ATTRIBUTES)]
ntdll.NtQueryDirectoryObject.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.ULONG, wt.BOOLEAN, wt.BOOLEAN, ctypes.POINTER(wt.ULONG), ctypes.POINTER(wt.ULONG)]
ntdll.NtQueryObject.argtypes = [wt.HANDLE, ctypes.c_uint, ctypes.c_void_p, wt.ULONG, ctypes.POINTER(wt.ULONG)]
ntdll.NtQuerySystemInformation.argtypes = [ctypes.c_uint, ctypes.c_void_p, wt.ULONG, ctypes.POINTER(wt.ULONG)]
shell32.ShellExecuteExW.argtypes = [ctypes.POINTER(SHELLEXECUTEINFOW)]

def snapshot_processes():
    h = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if h == ctypes.c_void_p(-1).value:
        return {}
    pe = PROCESSENTRY32W(); pe.dwSize = ctypes.sizeof(pe); outd = {}
    try:
        ok = k32.Process32FirstW(h, ctypes.byref(pe))
        while ok:
            outd[int(pe.th32ProcessID)] = {'name': pe.szExeFile, 'ppid': int(pe.th32ParentProcessID)}
            ok = k32.Process32NextW(h, ctypes.byref(pe))
    finally:
        k32.CloseHandle(h)
    return outd

def process_details(pid):
    h = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid); d = {}
    if not h:
        return d
    try:
        n = wt.DWORD(1024); b = ctypes.create_unicode_buffer(n.value)
        if k32.QueryFullProcessImageNameW(h, 0, b, ctypes.byref(n)):
            d['path'] = b.value
        c = FILETIME(); x = FILETIME(); k = FILETIME(); u = FILETIME()
        if k32.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(x), ctypes.byref(k), ctypes.byref(u)):
            ticks = (c.dwHighDateTime << 32) | c.dwLowDateTime
            if ticks:
                d['created'] = (dt.datetime(1601, 1, 1) + dt.timedelta(microseconds=ticks / 10)).isoformat(timespec='milliseconds')
    finally:
        k32.CloseHandle(h)
    return d

def relevant(name):
    n = name.upper()
    return any(x in n for x in ('TCLS', 'XTDL', 'TENPROXY', 'RAIL_', 'SHAREDMEM', 'TPF_SHARE'))

def session_ns():
    sid = wt.DWORD(); k32.ProcessIdToSessionId(k32.GetCurrentProcessId(), ctypes.byref(sid))
    return r'\Sessions\%d\BaseNamedObjects' % sid.value

def enum_dir(path):
    b = ctypes.create_unicode_buffer(path)
    us = UNICODE_STRING(len(path) * 2, (len(path) + 1) * 2, ctypes.cast(b, ctypes.c_void_p))
    oa = OBJECT_ATTRIBUTES(ctypes.sizeof(OBJECT_ATTRIBUTES), None, ctypes.pointer(us), 0, None, None)
    h = wt.HANDLE(); st = ntdll.NtOpenDirectoryObject(ctypes.byref(h), 1, ctypes.byref(oa))
    if st < 0:
        return []
    outv = []; buf = ctypes.create_string_buffer(65536); ctx = wt.ULONG(0); ret = wt.ULONG(0); first = True
    try:
        while True:
            st = ntdll.NtQueryDirectoryObject(h, buf, len(buf), True, first, ctypes.byref(ctx), ctypes.byref(ret)); first = False
            if st == 0x8000001A or st < 0:
                break
            base = ctypes.sizeof(UNICODE_STRING)
            nu = UNICODE_STRING.from_buffer_copy(buf.raw[:base]); tu = UNICODE_STRING.from_buffer_copy(buf.raw[base:base*2])
            if not nu.Length:
                break
            name = ctypes.wstring_at(nu.Buffer, nu.Length // 2); typ = ctypes.wstring_at(tu.Buffer, tu.Length // 2) if tu.Length else ''
            outv.append((name, typ))
    finally:
        k32.CloseHandle(h)
    return outv

def all_named():
    d = {}
    for ns in (r'\BaseNamedObjects', session_ns()):
        for name, typ in enum_dir(ns):
            if relevant(name):
                d[(ns, name, typ)] = time.time()
    return d

def query_handle_name(h):
    n = wt.ULONG(); buf = ctypes.create_string_buffer(32768)
    st = ntdll.NtQueryObject(h, 1, buf, len(buf), ctypes.byref(n))
    if st < 0 or n.value < ctypes.sizeof(UNICODE_STRING):
        return None
    us = UNICODE_STRING.from_buffer(buf)
    return ctypes.wstring_at(us.Buffer, us.Length // 2) if us.Buffer and us.Length else None

def all_handles():
    size = 32 * 1024 * 1024
    for _ in range(3):
        buf = ctypes.create_string_buffer(size); ret = wt.ULONG(); st = ntdll.NtQuerySystemInformation(64, buf, size, ctypes.byref(ret))
        if st >= 0:
            count = ctypes.c_size_t.from_buffer(buf, 0).value
            return count, (SYSTEM_HANDLE_TABLE_ENTRY_INFO_EX * count).from_buffer(buf, 16)
        if (st & 0xffffffff) != 0xC0000004:
            break
        size *= 2
    return 0, []

def holder_scan():
    count, arr = all_handles(); found = {}
    if not count:
        return found
    me = k32.GetCurrentProcess(); cache = {}
    for item in arr:
        pid = int(item.UniqueProcessId or 0)
        if pid not in cache:
            cache[pid] = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | 0x40, False, pid)
        ph = cache[pid]
        if not ph:
            continue
        dh = wt.HANDLE()
        if k32.DuplicateHandle(ph, wt.HANDLE(item.HandleValue), me, ctypes.byref(dh), 0, False, 2):
            try:
                name = query_handle_name(dh)
                if name and relevant(name):
                    found.setdefault(name, set()).add(pid)
            finally:
                k32.CloseHandle(dh)
    for h in cache.values():
        if h:
            k32.CloseHandle(h)
    return found

def snapshot_files():
    d = {}
    for root in WATCH:
        if not os.path.isdir(root):
            continue
        for base, _, files in os.walk(root):
            for fn in files:
                p = os.path.join(base, fn)
                try:
                    st = os.stat(p); d[p] = (st.st_size, st.st_mtime_ns)
                except OSError:
                    pass
    return d

def pattern_hits(path):
    try:
        data = open(path, 'rb').read(4 * 1024 * 1024)
    except OSError:
        return []
    hits = []
    for p in PATTERNS:
        if p.lower() in data.lower():
            hits.append(p.decode())
        elif p.decode().encode('utf-16le').lower() in data.lower():
            hits.append(p.decode() + '/UTF16')
    return hits

if not os.path.isfile(CLIENT):
    out('MISSING', CLIENT); raise SystemExit(2)

base_procs = snapshot_processes(); base_pids = set(base_procs); base_names = all_named(); base_files = snapshot_files()
out('OBSERVER_START', iso()); out('TARGET', CLIENT); out('WORKDIR', TCLS); out('BASE_PIDS', len(base_pids)); out('BASE_RELEVANT_NAMES', len(base_names))
for k in sorted(base_names): out('BASE_NAME', k[0], k[2], k[1])
last_holders = {}
for name, pids in sorted(holder_scan().items()):
    if name in {k[1] for k in base_names}:
        out('BASE_HOLDER', name, ','.join(map(str, sorted(pids))))

sei = SHELLEXECUTEINFOW(); sei.cbSize = ctypes.sizeof(sei); sei.fMask = 0x40 | 0x100; sei.lpVerb = 'runas'; sei.lpFile = CLIENT; sei.lpDirectory = TCLS; sei.nShow = 1
if not shell32.ShellExecuteExW(ctypes.byref(sei)) or not sei.hProcess:
    out('SHELLEXECUTE_FAIL', ctypes.get_last_error()); raise SystemExit(4)
root = int(k32.GetProcessId(sei.hProcess)); start = time.time(); end_at = start + 65.0
out('CREATE_PROCESS', iso(), 'ROOT_PID', root, 'MODE', 'ShellExecuteExW/runas')
seen = {}; first = {}; last = {}; details = {}; names = {}; exited = False; next_proc = start; next_name = start; next_holder = start
while time.time() < end_at:
    now = time.time()
    if now >= next_proc:
        procs = snapshot_processes(); new = set(procs) - base_pids
        for pid in sorted(new):
            info = procs[pid]
            if not relevant(info['name']) and pid != root and info.get('ppid') not in ({root} | set(seen)):
                continue
            if pid not in first:
                first[pid] = now; details[pid] = process_details(pid); out('PROCESS_FIRST_SEEN', iso(now), pid, 'PPID', info['ppid'], 'NAME', info['name'], 'PATH', details[pid].get('path',''), 'CREATED', details[pid].get('created',''))
            seen[pid] = info; last[pid] = now
        code = wt.DWORD()
        if not exited and k32.GetExitCodeProcess(sei.hProcess, ctypes.byref(code)) and code.value != 259:
            exited = True; out('ROOT_EXIT', iso(now), 'PID', root, 'EXITCODE', int(code.value))
        next_proc += 0.10
    if now >= next_name:
        for key in all_named():
            if key not in base_names:
                if key not in names:
                    names[key] = now; out('NAMED_FIRST_SEEN', iso(now), 'NS', key[0], 'TYPE', key[2], 'NAME', key[1])
                names[key] = now
        next_name += 0.20
    if now >= next_holder:
        for name, pids in holder_scan().items():
            if name in {k[1] for k in base_names}:
                continue
            key = (name, tuple(sorted(pids)))
            if key not in last_holders:
                out('HOLDER_FIRST_SEEN', iso(now), 'NAME', name, 'PIDS', ','.join(map(str, sorted(pids))))
            last_holders[key] = now
        next_holder += 1.0
final = snapshot_processes(); code = wt.DWORD(); k32.GetExitCodeProcess(sei.hProcess, ctypes.byref(code))
out('OBSERVE_END', iso(), 'SAMPLES_PROC', int((time.time()-start)/0.10), 'ROOT_EXITCODE', None if code.value == 259 else int(code.value))
for pid in sorted(first):
    info = seen.get(pid) or final.get(pid) or {'name':'','ppid':0}
    out('PROCESS_SUMMARY', pid, 'PPID', info.get('ppid',0), 'NAME', info.get('name',''), 'FIRST', iso(first[pid]), 'LAST_VISIBLE', iso(last.get(pid, first[pid])), 'PATH', details.get(pid,{}).get('path',''), 'CREATED', details.get(pid,{}).get('created',''))
for key in sorted(names):
    out('NAMED_SUMMARY', key[0], key[2], key[1], 'FIRST_VISIBLE', iso(names[key]), 'LAST_VISIBLE', iso(names[key]))
for (name, pids), tseen in sorted(last_holders.items()):
    out('HOLDER_SUMMARY', name, 'PIDS', ','.join(map(str, pids)), 'LAST_VISIBLE', iso(tseen))
post = snapshot_files(); changed = [p for p, m in post.items() if p not in base_files or base_files[p] != m]
out('CHANGED_OR_NEW_FILES', len(changed))
for p in sorted(changed):
    try: out('FILE', iso(os.path.getmtime(p)), os.path.getsize(p), p, 'PATTERNS', ','.join(pattern_hits(p)))
    except OSError: pass
out('ALIVE_AT_END_NO_STOP' if root in final else 'NO_STOP_NEEDED', root)
k32.CloseHandle(sei.hProcess); out('OBSERVER_END', iso())
