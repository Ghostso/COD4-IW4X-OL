import ctypes
import ctypes.wintypes as wt
import os
import sys
import time

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
GAME = os.path.join(ROOT, "COD OL", "codoMP_client_shipRetail.exe")
GAMEDIR = os.path.join(ROOT, "COD OL")

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32 = ctypes.WinDLL("user32", use_last_error=True)


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD),
        ("th32DefaultHeapID", ctypes.c_void_p), ("th32ModuleID", wt.DWORD),
        ("cntThreads", wt.DWORD), ("th32ParentProcessID", wt.DWORD),
        ("pcPriClassBase", ctypes.c_long), ("dwFlags", wt.DWORD), ("szExeFile", wt.WCHAR * 260),
    ]


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD), ("th32ModuleID", wt.DWORD), ("th32ProcessID", wt.DWORD),
        ("GlblcntUsage", wt.DWORD), ("ProccntUsage", wt.DWORD), ("modBaseAddr", ctypes.c_void_p),
        ("modBaseSize", wt.DWORD), ("hModule", wt.HANDLE), ("szModule", wt.WCHAR * 256),
        ("szExePath", wt.WCHAR * 260),
    ]


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", wt.DWORD), ("lpReserved", wt.LPWSTR), ("lpDesktop", wt.LPWSTR),
        ("lpTitle", wt.LPWSTR), ("dwX", wt.DWORD), ("dwY", wt.DWORD),
        ("dwXSize", wt.DWORD), ("dwYSize", wt.DWORD), ("dwXCountChars", wt.DWORD),
        ("dwYCountChars", wt.DWORD), ("dwFillAttribute", wt.DWORD), ("dwFlags", wt.DWORD),
        ("wShowWindow", wt.WORD), ("cbReserved2", wt.WORD), ("lpReserved2", ctypes.c_void_p),
        ("hStdInput", wt.HANDLE), ("hStdOutput", wt.HANDLE), ("hStdError", wt.HANDLE),
    ]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [("hProcess", wt.HANDLE), ("hThread", wt.HANDLE), ("dwProcessId", wt.DWORD), ("dwThreadId", wt.DWORD)]


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wt.DWORD), ("PartitionId", wt.DWORD), ("RegionSize", ctypes.c_size_t),
        ("State", wt.DWORD), ("Protect", wt.DWORD), ("Type", wt.DWORD),
    ]


k32.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
k32.Process32FirstW.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
k32.Process32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
k32.Module32FirstW.argtypes = [wt.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
k32.Module32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
k32.CloseHandle.argtypes = [wt.HANDLE]
k32.CreateProcessW.argtypes = [wt.LPCWSTR, wt.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, wt.BOOL, wt.DWORD, ctypes.c_void_p, wt.LPCWSTR, ctypes.POINTER(STARTUPINFOW), ctypes.POINTER(PROCESS_INFORMATION)]
k32.CreateProcessW.restype = wt.BOOL
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.OpenProcess.restype = wt.HANDLE
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.POINTER(MEMORY_BASIC_INFORMATION), ctypes.c_size_t]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.ReadProcessMemory.restype = wt.BOOL
k32.QueryFullProcessImageNameW.argtypes = [wt.HANDLE, wt.DWORD, wt.LPWSTR, ctypes.POINTER(wt.DWORD)]
k32.QueryFullProcessImageNameW.restype = wt.BOOL
k32.TerminateProcess.argtypes = [wt.HANDLE, wt.UINT]

user32.EnumWindows.argtypes = [ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM), wt.LPARAM]
user32.EnumWindows.restype = wt.BOOL
user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
user32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
user32.GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]


def procs():
    h = k32.CreateToolhelp32Snapshot(2, 0)
    res = {}
    if h == ctypes.c_void_p(-1).value:
        return res
    e = PROCESSENTRY32W()
    e.dwSize = ctypes.sizeof(e)
    ok = k32.Process32FirstW(h, ctypes.byref(e))
    while ok:
        res[int(e.th32ProcessID)] = (int(e.th32ParentProcessID), e.szExeFile)
        ok = k32.Process32NextW(h, ctypes.byref(e))
    k32.CloseHandle(h)
    return res


def modules(pid):
    h = k32.CreateToolhelp32Snapshot(0x18, pid)
    if h == ctypes.c_void_p(-1).value:
        return []
    outv = []
    e = MODULEENTRY32W()
    e.dwSize = ctypes.sizeof(e)
    ok = k32.Module32FirstW(h, ctypes.byref(e))
    while ok:
        outv.append((e.szExePath, int(e.modBaseAddr or 0), int(e.modBaseSize)))
        ok = k32.Module32NextW(h, ctypes.byref(e))
    k32.CloseHandle(h)
    return outv


def module_for(addr, mods):
    for path, base, size in mods:
        if base <= addr < base + size:
            return path, addr - base
    return None, None


def find_all(hay, needle):
    out = []
    pos = 0
    while True:
        pos = hay.find(needle, pos)
        if pos < 0:
            return out
        out.append(pos)
        pos += 1


def readable(prot):
    return bool(prot & 0xFE) and not (prot & (0x100 | 0x80 | 0x1000000))


def exec_prot(prot):
    return bool(prot & 0xF0)


if not os.path.isfile(GAME):
    print("MISSING", GAME)
    sys.exit(2)

si = STARTUPINFOW()
si.cb = ctypes.sizeof(si)
pi = PROCESS_INFORMATION()
cmd = ctypes.create_unicode_buffer('"' + GAME + '"')
if not k32.CreateProcessW(GAME, cmd, None, None, False, 0, None, GAMEDIR, ctypes.byref(si), ctypes.byref(pi)):
    print("CREATE_FAIL", ctypes.get_last_error())
    sys.exit(4)
pid = int(pi.dwProcessId)
print("PID", pid, "PARENT", os.getpid())

target_windows = []


def enum_proc(hwnd, lp):
    wpid = wt.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
    if wpid.value == pid:
        b = ctypes.create_unicode_buffer(4096)
        user32.GetWindowTextW(hwnd, b, len(b))
        c = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, c, len(c))
        target_windows.append((hwnd, c.value, b.value))
    return True


end = time.time() + 25
while time.time() < end:
    target_windows.clear()
    user32.EnumWindows(ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)(enum_proc), 0)
    if any("致命" in t for _, _, t in target_windows):
        break
    time.sleep(0.25)

print("WINDOWS", len(target_windows))
for hwnd, cls, text in target_windows:
    print("WIN", hex(hwnd), cls, repr(text))

allp = procs()
print("PROCESS_TREE")
print("PID", pid, "PPID", allp.get(pid, (0, ""))[0], "IMAGE", allp.get(pid, (0, ""))[1])

h = k32.OpenProcess(0x0010 | 0x0400, False, pid)
if not h:
    print("OPEN_FAIL", ctypes.get_last_error())
    k32.TerminateProcess(pi.hProcess, 0)
    sys.exit(5)

patterns = {
    "WIN_NO_TCLS_ascii": b"WIN_NO_TCLS",
    "WIN_NO_TCLS_utf16": "WIN_NO_TCLS".encode("utf-16le"),
    "TCLS_folder_utf16": "TCLS文件夹内的Client.exe".encode("utf-16le"),
}
mods = modules(pid)
print("MODULES", len(mods))

string_addrs = {k: [] for k in patterns}
regions = []
addr = 0
while addr < 0x7FFF0000:
    mbi = MEMORY_BASIC_INFORMATION()
    if not k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
        break
    size = mbi.RegionSize
    if mbi.State == 0x1000 and readable(mbi.Protect) and size > 0:
        regions.append((int(mbi.BaseAddress or 0), size, mbi.Protect, bool(exec_prot(mbi.Protect))))
    addr += max(size, 1)

print("REGIONS", len(regions))
for base, size, prot, isexec in regions:
    buf = ctypes.create_string_buffer(size if size <= 16 * 1024 * 1024 else 16 * 1024 * 1024)
    chunk = len(buf)
    off = 0
    while off < size:
        n = min(chunk, size - off)
        read = ctypes.c_size_t()
        if not k32.ReadProcessMemory(h, ctypes.c_void_p(base + off), buf, n, ctypes.byref(read)):
            off += n
            continue
        data = buf.raw[:read.value]
        for name, pat in patterns.items():
            for pos in find_all(data, pat):
                string_addrs[name].append(base + off + pos)
        if isexec:
            # Store executable region data for pointer scan later.
            pass
        off += n

print("STRING_HITS")
for name, hits in string_addrs.items():
    print(name, len(hits))
    for a in hits[:20]:
        path, rva = module_for(a, mods)
        print(" ", hex(a), path, ("+0x%X" % rva) if rva is not None else "")

print("PTR_SCAN")
for name, hits in string_addrs.items():
    for target in hits:
        pat = ctypes.c_uint32(target & 0xFFFFFFFF)
        patb = bytes(pat)
        found = []
        for base, size, prot, isexec in regions:
            if not isexec:
                continue
            buf = ctypes.create_string_buffer(16 * 1024 * 1024)
            chunk = len(buf)
            off = 0
            while off < size:
                n = min(chunk, size - off)
                read = ctypes.c_size_t()
                if not k32.ReadProcessMemory(h, ctypes.c_void_p(base + off), buf, n, ctypes.byref(read)):
                    off += n
                    continue
                data = buf.raw[:read.value]
                for pos in find_all(data, patb):
                    found.append(base + off + pos)
                off += n
        if found:
            print("PTR", name, "target", hex(target), "count", len(found))
            for a in found[:50]:
                path, rva = module_for(a, mods)
                print("  ", hex(a), path, ("+0x%X" % rva) if rva is not None else "")

k32.TerminateProcess(pi.hProcess, 0)
k32.CloseHandle(h)
k32.CloseHandle(pi.hThread)
k32.CloseHandle(pi.hProcess)
print("END")
