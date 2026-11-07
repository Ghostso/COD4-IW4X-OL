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
    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(si)
    pi = PROCESS_INFORMATION()
    cmd = ctypes.create_unicode_buffer('"' + str(GAME_EXP) + '" -q')
    k32.CreateProcessW(str(GAME_EXP), cmd, None, None, False, 0, None, str(EXP), ctypes.byref(si), ctypes.byref(pi))
    pid = int(pi.dwProcessId)
    print("PID", pid)
    end = time.time() + 20
    while time.time() < end:
        if any("致命错误" in t for t in windows_for(pid)):
            break
        time.sleep(0.2)
    h = k32.OpenProcess(0x0010 | 0x0400, False, pid)
    if not h:
        return 5
    mods = modules(pid)

    def read_mem(va, size):
        buf = ctypes.create_string_buffer(size)
        rd = ctypes.c_size_t()
        if not k32.ReadProcessMemory(h, ctypes.c_void_p(va), buf, size, ctypes.byref(rd)):
            return b""
        return buf.raw[:rd.value]

    md = Cs(CS_ARCH_X86, CS_MODE_32)
    print("FUNC_AROUND_621AC6")
    for va in [0x621A00, 0x621B00, 0x7E9600, 0x7E9900, 0x808000, 0x4FCE00, 0x4FD000, 0x4FD900]:
        data = read_mem(va, 0x600)
        print("=== ", hex(va))
        for ins in md.disasm(data, va):
            print("  ", "%08X %-22s %-8s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))

    regions = []
    addr = 0
    while addr < 0x7FFF0000:
        mbi = MEMORY_BASIC_INFORMATION()
        if not k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
            break
        if mbi.State == 0x1000 and mbi.Protect & 0xF0 and mbi.RegionSize:
            regions.append((int(mbi.BaseAddress or 0), mbi.RegionSize))
        addr += max(mbi.RegionSize, 1)

    for target in [0x621AC6, 0x6212C0]:
        hits = []
        for base, size in regions:
            off = 0
            while off < size:
                data = read_mem(base + off, min(8 * 1024 * 1024, size - off))
                if not data:
                    break
                for i in range(len(data) - 5):
                    if data[i] == 0xE8:
                        rel = int.from_bytes(data[i+1:i+5], "little", signed=True)
                        if base + off + i + 5 + rel == target:
                            hits.append(base + off + i)
                off += len(data)
        print("CALLERS_OF", hex(target), len(hits))
        for va in hits[:50]:
            path, rva = module_for(va, mods)
            print("  CALLER", hex(va), path, ("+0x%X" % rva) if rva is not None else "")

    k32.TerminateProcess(pi.hProcess, 0)
    k32.CloseHandle(h)
    k32.CloseHandle(pi.hThread)
    k32.CloseHandle(pi.hProcess)
    return 0


if __name__ == "__main__":
    sys.exit(main())
