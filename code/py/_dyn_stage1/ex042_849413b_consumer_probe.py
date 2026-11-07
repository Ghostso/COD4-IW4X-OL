import ctypes
import ctypes.wintypes as wt
import sys
import time
from pathlib import Path

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
EXP = Path(ROOT) / "工具" / "EX035_DIR"
GAME_EXP = EXP / "codoMP_client_shipRetail.exe"

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32 = ctypes.WinDLL("user32", use_last_error=True)


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


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD), ("th32ModuleID", wt.DWORD), ("th32ProcessID", wt.DWORD),
        ("GlblcntUsage", wt.DWORD), ("ProccntUsage", wt.DWORD), ("modBaseAddr", ctypes.c_void_p),
        ("modBaseSize", wt.DWORD), ("hModule", wt.HANDLE), ("szModule", wt.WCHAR * 256),
        ("szExePath", wt.WCHAR * 260),
    ]


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wt.DWORD), ("PartitionId", wt.DWORD), ("RegionSize", ctypes.c_size_t),
        ("State", wt.DWORD), ("Protect", wt.DWORD), ("Type", wt.DWORD),
    ]


k32.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
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
k32.TerminateProcess.argtypes = [wt.HANDLE, wt.UINT]

user32.EnumWindows.argtypes = [ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM), wt.LPARAM]
user32.EnumWindows.restype = wt.BOOL
user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
user32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]


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


def windows_for(pid):
    found = []

    def enum_proc(hwnd, lp):
        wpid = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
        if wpid.value == pid:
            b = ctypes.create_unicode_buffer(4096)
            user32.GetWindowTextW(hwnd, b, len(b))
            found.append(b.value)
        return True

    user32.EnumWindows(ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)(enum_proc), 0)
    return found


def main():
    if not GAME_EXP.is_file():
        print("MISSING_EXP")
        return 1
    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(si)
    pi = PROCESS_INFORMATION()
    cmd = ctypes.create_unicode_buffer('"' + str(GAME_EXP) + '" -q')
    ok = k32.CreateProcessW(str(GAME_EXP), cmd, None, None, False, 0, None, str(EXP), ctypes.byref(si), ctypes.byref(pi))
    if not ok:
        print("CREATE_FAIL", ctypes.get_last_error())
        return 4
    pid = int(pi.dwProcessId)
    print("PID", pid)
    end = time.time() + 20
    while time.time() < end:
        if any("致命错误" in t for t in windows_for(pid)):
            break
        time.sleep(0.2)

    h = k32.OpenProcess(0x0010 | 0x0400, False, pid)
    if not h:
        print("OPEN_FAIL", ctypes.get_last_error())
        k32.TerminateProcess(pi.hProcess, 0)
        return 5
    mods = modules(pid)

    def read_mem(va, size):
        buf = ctypes.create_string_buffer(size)
        rd = ctypes.c_size_t()
        if not k32.ReadProcessMemory(h, ctypes.c_void_p(va), buf, size, ctypes.byref(rd)):
            return b""
        return buf.raw[:rd.value]

    flag = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x849413B
    pat = bytes(ctypes.c_uint32(flag))
    regions = []
    addr = 0
    while addr < 0x7FFF0000:
        mbi = MEMORY_BASIC_INFORMATION()
        if not k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
            break
        if mbi.State == 0x1000 and mbi.Protect & 0xFE and not (mbi.Protect & (0x100 | 0x80 | 0x1000000)) and mbi.RegionSize:
            regions.append((int(mbi.BaseAddress or 0), mbi.RegionSize, mbi.Protect, bool(mbi.Protect & 0xF0)))
        addr += max(mbi.RegionSize, 1)

    refs = []
    deep_targets = {0x6213B9, 0x6214C5, 0x802423, 0x802CD3, 0x637770, 0x755873}
    for base, size, prot, isexec in regions:
        if not isexec:
            continue
        chunk = 16 * 1024 * 1024
        off = 0
        while off < size:
            n = min(chunk, size - off)
            data = read_mem(base + off, n)
            if data:
                for pos in find_all(data, pat):
                    refs.append(base + off + pos)
            off += n

    print("REF_COUNT", len(refs))
    for va in sorted(set(refs)):
        path, rva = module_for(va, mods)
        print("REF", hex(va), path, ("+0x%X" % rva) if rva is not None else "")
        if va in deep_targets:
            if va == 0x755873:
                start = va - 0x2000
                size = 0x2800
            else:
                start = va - 0x1000
                size = 0x1800
        else:
            start = va - 0x300
            size = 0x600
        data = read_mem(start, size)
        md = Cs(CS_ARCH_X86, CS_MODE_32)
        for ins in md.disasm(data, start):
            print("  ", "%08X %-22s %-8s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))

    print("STRINGS")
    for va, n in [(0xDAB000, 128), (0xDAE091, 64), (0xDB7B80, 64), (0xDC6610, 64),
                  (0xDE15BC, 64), (0xDE15D4, 64), (0xDE15EC, 64), (0x81A9C50, 64)]:
        raw = read_mem(va, n)
        text = raw.split(b"\0")[0].decode("utf-8", "replace")
        print(hex(va), repr(text))

    print("FUNC_DUMP")
    for va in [0x759F50, 0x621B00, 0x643300, 0x780140]:
        data = read_mem(va, 0x180)
        md = Cs(CS_ARCH_X86, CS_MODE_32)
        print("=== ", hex(va))
        for ins in md.disasm(data, va):
            print("  ", "%08X %-22s %-8s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))

    print("GLOBAL", read_mem(flag, 1).hex())
    k32.TerminateProcess(pi.hProcess, 0)
    k32.CloseHandle(h)
    k32.CloseHandle(pi.hThread)
    k32.CloseHandle(pi.hProcess)
    return 0


if __name__ == "__main__":
    sys.exit(main())
