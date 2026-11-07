import ctypes
import ctypes.wintypes as wt
import datetime as dt
import os
import re
import subprocess
import sys
import time

ROOT = r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL'
TCLS = os.path.join(ROOT, 'TCLS')
CLIENT = os.path.join(TCLS, 'Client.exe')
WATCH_DIRS = [
    TCLS,
    os.path.join(ROOT, 'TenproxyLog'),
    os.path.join(ROOT, 'Logs'),
    r'D:\BaiduNetdiskDownload\使命召唤OL\WeGame\tcls',
]
PATTERNS = [b'TCLS_SHAREDMEMEMORY', b'StartGame', b'LaunchGame', b'RunGame',
            b'CreateFileMapping', b'MapViewOfFile', b'GetGameSignatrue',
            b'GetJumpSignatrue', b'WIN_NO_TCLS', b'OpenFileMapping']

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
ntdll = ctypes.WinDLL('ntdll', use_last_error=True)
shell32 = ctypes.WinDLL('shell32', use_last_error=True)

TH32CS_SNAPPROCESS = 0x2
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
PROCESS_TERMINATE = 0x0001
SYNCHRONIZE = 0x00100000
WAIT_OBJECT_0 = 0

class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ('dwSize', wt.DWORD), ('cntUsage', wt.DWORD), ('th32ProcessID', wt.DWORD),
        ('th32DefaultHeapID', ctypes.c_void_p), ('th32ModuleID', wt.DWORD),
        ('cntThreads', wt.DWORD), ('th32ParentProcessID', wt.DWORD),
        ('pcPriClassBase', ctypes.c_long), ('dwFlags', wt.DWORD),
        ('szExeFile', wt.WCHAR * 260),
    ]

class FILETIME(ctypes.Structure):
    _fields_ = [('dwLowDateTime', wt.DWORD), ('dwHighDateTime', wt.DWORD)]

class UNICODE_STRING(ctypes.Structure):
    _fields_ = [('Length', wt.USHORT), ('MaximumLength', wt.USHORT), ('Buffer', ctypes.c_void_p)]

class OBJECT_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ('Length', wt.ULONG), ('RootDirectory', wt.HANDLE),
        ('ObjectName', ctypes.POINTER(UNICODE_STRING)), ('Attributes', wt.ULONG),
        ('SecurityDescriptor', ctypes.c_void_p), ('SecurityQualityOfService', ctypes.c_void_p),
    ]

class SHELLEXECUTEINFOW(ctypes.Structure):
    _fields_ = [
        ('cbSize', wt.DWORD), ('fMask', wt.ULONG), ('hwnd', wt.HWND),
        ('lpVerb', wt.LPCWSTR), ('lpFile', wt.LPCWSTR), ('lpParameters', wt.LPCWSTR),
        ('lpDirectory', wt.LPCWSTR), ('nShow', ctypes.c_int), ('hInstApp', wt.HANDLE),
        ('lpIDList', ctypes.c_void_p), ('lpClass', wt.LPCWSTR), ('hkeyClass', wt.HANDLE),
        ('dwHotKey', wt.DWORD), ('hIcon', wt.HANDLE), ('hProcess', wt.HANDLE),
    ]
class SYSTEM_HANDLE_TABLE_ENTRY_INFO_EX(ctypes.Structure):
    _fields_ = [
        ('Object', ctypes.c_void_p), ('UniqueProcessId', ctypes.c_void_p),
        ('HandleValue', ctypes.c_void_p), ('GrantedAccess', wt.ULONG),
        ('CreatorBackTraceIndex', wt.USHORT), ('ObjectTypeIndex', wt.USHORT),
        ('HandleAttributes', wt.ULONG), ('Reserved', wt.ULONG),
    ]

k32.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
k32.Process32FirstW.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
k32.Process32FirstW.restype = wt.BOOL
k32.Process32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
k32.Process32NextW.restype = wt.BOOL
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.OpenProcess.restype = wt.HANDLE
k32.QueryFullProcessImageNameW.argtypes = [wt.HANDLE, wt.DWORD, wt.LPWSTR, ctypes.POINTER(wt.DWORD)]
k32.QueryFullProcessImageNameW.restype = wt.BOOL
k32.GetProcessTimes.argtypes = [wt.HANDLE, ctypes.POINTER(FILETIME), ctypes.POINTER(FILETIME), ctypes.POINTER(FILETIME), ctypes.POINTER(FILETIME)]
k32.GetProcessTimes.restype = wt.BOOL
k32.TerminateProcess.argtypes = [wt.HANDLE, wt.UINT]
k32.TerminateProcess.restype = wt.BOOL
k32.WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]
k32.WaitForSingleObject.restype = wt.DWORD
k32.CloseHandle.argtypes = [wt.HANDLE]
k32.GetProcessId.argtypes = [wt.HANDLE]
k32.GetProcessId.restype = wt.DWORD
k32.GetExitCodeProcess.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
k32.GetExitCodeProcess.restype = wt.BOOL
shell32.ShellExecuteExW.argtypes = [ctypes.POINTER(SHELLEXECUTEINFOW)]
shell32.ShellExecuteExW.restype = wt.BOOL

ntdll.NtOpenDirectoryObject.argtypes = [ctypes.POINTER(wt.HANDLE), wt.DWORD, ctypes.POINTER(OBJECT_ATTRIBUTES)]
ntdll.NtOpenDirectoryObject.restype = ctypes.c_long
ntdll.NtQueryDirectoryObject.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.ULONG, wt.BOOLEAN, wt.BOOLEAN, ctypes.POINTER(wt.ULONG), ctypes.POINTER(wt.ULONG)]
ntdll.NtQueryDirectoryObject.restype = ctypes.c_long
k32.DuplicateHandle.argtypes = [wt.HANDLE, wt.HANDLE, wt.HANDLE, ctypes.POINTER(wt.HANDLE), wt.DWORD, wt.BOOL, wt.DWORD]
k32.DuplicateHandle.restype = wt.BOOL
ntdll.NtQueryObject.argtypes = [wt.HANDLE, ctypes.c_uint, ctypes.c_void_p, wt.ULONG, ctypes.POINTER(wt.ULONG)]
ntdll.NtQueryObject.restype = ctypes.c_long
ntdll.NtQuerySystemInformation.argtypes = [ctypes.c_uint, ctypes.c_void_p, wt.ULONG, ctypes.POINTER(wt.ULONG)]
ntdll.NtQuerySystemInformation.restype = ctypes.c_long

def iso(ts=None):
    return dt.datetime.fromtimestamp(ts if ts is not None else time.time()).isoformat(timespec='milliseconds')

def snapshot_processes():
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    out = {}
    if snap == INVALID_HANDLE_VALUE:
        return out
    e = PROCESSENTRY32W(); e.dwSize = ctypes.sizeof(e)
    ok = k32.Process32FirstW(snap, ctypes.byref(e))
    while ok:
        out[int(e.th32ProcessID)] = {
            'pid': int(e.th32ProcessID), 'ppid': int(e.th32ParentProcessID),
            'name': e.szExeFile, 'threads': int(e.cntThreads),
        }
        ok = k32.Process32NextW(snap, ctypes.byref(e))
    k32.CloseHandle(snap)
    return out

def process_details(pid):
    h = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    d = {}
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
                d['created'] = dt.datetime(1601, 1, 1) + dt.timedelta(microseconds=ticks / 10)
    finally:
        k32.CloseHandle(h)
    return d

def is_relevant_name(name):
    n = name.upper()
    return any(x in n for x in ('TCLS', 'XTDL', 'TENPROXY', 'RAIL_', 'SHAREDMEM'))

def session_namespace():
    sid = wt.DWORD()
    pid = k32.GetCurrentProcessId()
    if k32.ProcessIdToSessionId(pid, ctypes.byref(sid)):
        return r'\Sessions\%d\BaseNamedObjects' % sid.value
    return r'\Sessions\1\BaseNamedObjects'

def enum_named_directory(path):
    p = path.encode('utf-16le').decode('utf-16le')
    b = ctypes.create_unicode_buffer(p)
    us = UNICODE_STRING(len(p) * 2, (len(p) + 1) * 2, ctypes.cast(b, ctypes.c_void_p))
    oa = OBJECT_ATTRIBUTES(ctypes.sizeof(OBJECT_ATTRIBUTES), None, ctypes.pointer(us), 0, None, None)
    h = wt.HANDLE()
    st = ntdll.NtOpenDirectoryObject(ctypes.byref(h), 1, ctypes.byref(oa))
    if st < 0:
        return []
    out = []
    buf = ctypes.create_string_buffer(65536)
    ctx = wt.ULONG(0); ret = wt.ULONG(0); first = True
    try:
        while True:
            st = ntdll.NtQueryDirectoryObject(h, buf, len(buf), True, first, ctypes.byref(ctx), ctypes.byref(ret))
            first = False
            if st == 0x8000001A:
                break
            if st < 0:
                break
            base = ctypes.sizeof(UNICODE_STRING)
            nu = UNICODE_STRING.from_buffer_copy(buf.raw[:base])
            tu = UNICODE_STRING.from_buffer_copy(buf.raw[base:base * 2])
            if not nu.Length:
                break
            name = ctypes.wstring_at(nu.Buffer, nu.Length // 2)
            typ = ctypes.wstring_at(tu.Buffer, tu.Length // 2) if tu.Length else ''
            out.append((name, typ))
    finally:
        k32.CloseHandle(h)
    return out

def query_handle_name(h):
    n = wt.ULONG(); buf = ctypes.create_string_buffer(32768)
    st = ntdll.NtQueryObject(h, 1, buf, len(buf), ctypes.byref(n))
    if st < 0 or n.value < ctypes.sizeof(UNICODE_STRING):
        return None
    us = UNICODE_STRING.from_buffer(buf)
    if not us.Buffer or not us.Length:
        return None
    return ctypes.wstring_at(us.Buffer, us.Length // 2)

def all_handle_entries():
    size = 32 * 1024 * 1024
    for _ in range(4):
        buf = ctypes.create_string_buffer(size); ret = wt.ULONG()
        st = ntdll.NtQuerySystemInformation(64, buf, size, ctypes.byref(ret))
        if st >= 0:
            count = ctypes.c_size_t.from_buffer(buf, 0).value
            arr = (SYSTEM_HANDLE_TABLE_ENTRY_INFO_EX * count).from_buffer(buf, 16)
            return count, arr
        if (st & 0xffffffff) != 0xC0000004:
            break
        size = min(size * 2, 256 * 1024 * 1024)
    return 0, []

def handle_names_for_pids(pids):
    count, arr = all_handle_entries()
    found = {}
    for pid in pids:
        found[pid] = []
    if not count:
        return found
    current = k32.GetCurrentProcess()
    for item in arr:
        pid = int(item.UniqueProcessId or 0)
        if pid not in found:
            continue
        ph = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | 0x40, False, pid)
        if not ph:
            continue
        dh = wt.HANDLE()
        if k32.DuplicateHandle(ph, wt.HANDLE(item.HandleValue), current, ctypes.byref(dh), 0, False, 2):
            try:
                name = query_handle_name(dh)
                if name and is_relevant_name(name):
                    found[pid].append((int(item.HandleValue), int(item.ObjectTypeIndex), int(item.GrantedAccess), name))
            finally:
                k32.CloseHandle(dh)
        k32.CloseHandle(ph)
    return found

def snapshot_files(dirs):
    out = {}
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for base, _, files in os.walk(d):
            for fn in files:
                p = os.path.join(base, fn)
                try:
                    st = os.stat(p)
                    out[p] = (st.st_size, st.st_mtime_ns)
                except OSError:
                    pass
    return out

def pattern_hits(path):
    hits = set()
    try:
        with open(path, 'rb') as f:
            data = f.read(4 * 1024 * 1024)
    except OSError:
        return hits
    for p in PATTERNS:
        if p.lower() in data.lower():
            hits.add(p.decode('ascii'))
        u = p.decode('ascii').encode('utf-16le')
        if u.lower() in data.lower():
            hits.add(p.decode('ascii') + '/UTF16')
    return hits

def descendants(root_pid, procs):
    selected = {root_pid}
    changed = True
    while changed:
        changed = False
        for pid, p in procs.items():
            if pid not in selected and p['ppid'] in selected:
                selected.add(pid); changed = True
    return selected

def stop_tree(root_pid, procs):
    selected = descendants(root_pid, procs)
    # Deepest descendants first, using current parent chain.
    rank = {}
    for pid in selected:
        r = 0; x = pid
        while x in procs and r < 32:
            r += 1; x = procs[x]['ppid']
            if x == root_pid:
                break
        rank[pid] = r
    for pid in sorted(selected, key=lambda x: rank.get(x, 0), reverse=True):
        h = k32.OpenProcess(PROCESS_TERMINATE | SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if h:
            try:
                k32.TerminateProcess(h, 0)
                if pid == root_pid:
                    k32.WaitForSingleObject(h, 2000)
            finally:
                k32.CloseHandle(h)
    return sorted(selected)

if not os.path.isfile(CLIENT):
    print('MISSING', CLIENT); raise SystemExit(2)

base = snapshot_processes()
base_pids = set(base)
base_files = snapshot_files(WATCH_DIRS)
print('OBSERVER_START', iso())
print('TARGET', CLIENT)
print('WORKDIR', TCLS)
print('BASE_PIDS', len(base_pids))
print('BASE_FILE_COUNT', len(base_files))

def process_exit_code(handle):
    code = wt.DWORD(0)
    if not k32.GetExitCodeProcess(handle, ctypes.byref(code)):
        return None
    return None if code.value == 259 else int(code.value)

start = time.time()
sei = SHELLEXECUTEINFOW()
sei.cbSize = ctypes.sizeof(sei)
sei.fMask = 0x00000040 | 0x00000100  # NOCLOSEPROCESS | NOASYNC
sei.lpVerb = 'runas'
sei.lpFile = CLIENT
sei.lpDirectory = TCLS
sei.nShow = 1
if not shell32.ShellExecuteExW(ctypes.byref(sei)) or not sei.hProcess:
    err = ctypes.get_last_error()
    if err == 1223:
        print('UAC_CANCELLED', iso(), flush=True)
        raise SystemExit(3)
    print('SHELLEXECUTE_FAIL', iso(), 'ERR', err, flush=True)
    raise SystemExit(4)
root = int(k32.GetProcessId(sei.hProcess))
print('CREATE_PROCESS', iso(), 'ROOT_PID', root, 'MODE', 'ShellExecuteExW/runas', flush=True)

seen = {}
first_seen = {}
last_seen = {}
last_details = {}
name_first = {}
name_last = {}
holder_first = {}
holder_last = {}
samples = 0
end_at = start + 22.0
next_proc = start
next_name = start
next_holder = start

while time.time() < end_at:
    now = time.time()
    if now >= next_proc:
        procs = snapshot_processes()
        new = set(procs) - base_pids
        # Track new relevant processes and all descendants of our created root.
        root_selected = descendants(root, procs)
        for pid in sorted(new | root_selected):
            if pid not in procs:
                continue
            info = procs[pid]
            rel = pid in root_selected or is_relevant_name(info['name'])
            if not rel:
                continue
            if pid not in first_seen:
                first_seen[pid] = now
                last_details[pid] = process_details(pid)
                print('PROCESS_FIRST_SEEN', iso(now), pid, 'PPID', info['ppid'], 'NAME', info['name'], 'PATH', last_details[pid].get('path',''), 'CREATED', last_details[pid].get('created',''), flush=True)
            seen[pid] = info; last_seen[pid] = now
        # Announce disappearance based on prior sets if still absent in this snapshot.
        for pid in list(seen):
            if pid not in procs and pid != root:
                # Keep last-seen time; definitive disappearance is evaluated against 0.3s stale threshold.
                pass
        rc = process_exit_code(sei.hProcess)
        if rc is not None:
            print('ROOT_EXIT', iso(now), 'PID', root, 'EXITCODE', rc, flush=True)
        next_proc += 0.10

    if now >= next_name:
        for ns in (r'\BaseNamedObjects', session_namespace()):
            for name, typ in enum_named_directory(ns):
                if not is_relevant_name(name):
                    continue
                key = (ns, name, typ)
                if key not in name_first:
                    name_first[key] = now
                    print('NAMED_FIRST_SEEN', iso(now), 'NS', ns, 'TYPE', typ, 'NAME', name, flush=True)
                name_last[key] = now
        next_name += 0.20

    if now >= next_holder:
        procs = snapshot_processes()
        selected = descendants(root, procs)
        for pid, info in procs.items():
            if is_relevant_name(info['name']):
                selected.add(pid)
        hn = handle_names_for_pids(sorted(selected))
        for pid, items in hn.items():
            for hv, ti, ga, name in items:
                if not is_relevant_name(name):
                    continue
                key = (pid, name)
                if key not in holder_first:
                    holder_first[key] = now
                    print('HANDLE_FIRST_SEEN', iso(now), 'HOLDER_PID', pid, 'TYPE_INDEX', ti, 'ACCESS', hex(ga), 'NAME', name, flush=True)
                holder_last[key] = now
        next_holder += 0.50

    samples += 1
    time.sleep(0.05)

final_procs = snapshot_processes()
alive = root in final_procs
print('OBSERVE_END', iso(), 'ROOT_ALIVE', alive, 'ROOT_EXITCODE', process_exit_code(sei.hProcess), 'SAMPLES', samples)
for pid in sorted(first_seen):
    info = seen.get(pid) or final_procs.get(pid) or {'name':'','ppid':0}
    print('PROCESS_SUMMARY PID', pid, 'PPID', info.get('ppid',0), 'NAME', info.get('name',''),
          'FIRST', iso(first_seen[pid]), 'LAST_VISIBLE', iso(last_seen.get(pid, first_seen[pid])),
          'PATH', last_details.get(pid,{}).get('path',''), 'CREATED', last_details.get(pid,{}).get('created',''))

for key in sorted(name_first):
    print('NAMED_SUMMARY', 'NS', key[0], 'TYPE', key[1], 'NAME', key[2], 'FIRST_VISIBLE', iso(name_first[key]),
          'LAST_VISIBLE', iso(name_last.get(key, name_first[key])))

for key in sorted(holder_first):
    print('HANDLE_SUMMARY', 'HOLDER_PID', key[0], 'NAME', key[1], 'FIRST_VISIBLE', iso(holder_first[key]),
          'LAST_VISIBLE', iso(holder_last.get(key, holder_first[key])))

post_files = snapshot_files(WATCH_DIRS)
changed = []
for path, meta in post_files.items():
    if path not in base_files or base_files[path] != meta:
        changed.append(path)
print('CHANGED_OR_NEW_FILES', len(changed))
for path in sorted(changed):
    hits = pattern_hits(path)
    print('FILE', iso(os.path.getmtime(path)), os.path.getsize(path), path, 'PATTERNS', ','.join(sorted(hits)))

if alive:
    print('INTENTIONAL_STOP', iso(), 'ROOTS', root)
    stopped = stop_tree(root, final_procs)
    print('STOPPED_PIDS', ','.join(str(x) for x in stopped))
else:
    print('NO_STOP_NEEDED', iso())
k32.CloseHandle(sei.hProcess)
print('OBSERVER_END', iso())
