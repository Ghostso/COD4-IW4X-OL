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


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wt.DWORD), ("PartitionId", wt.DWORD), ("RegionSize", ctypes.c_size_t),
        ("State", wt.DWORD), ("Protect", wt.DWORD), ("Type", wt.DWORD),
    ]


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
    if not k32.CreateProcessW(str(GAME_EXP), cmd, None, None, False, 0, None, str(EXP), ctypes.byref(si), ctypes.byref(pi)):
        print("CREATE_FAIL")
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
        return 5

    def read_mem(va, size):
        buf = ctypes.create_string_buffer(size)
        rd = ctypes.c_size_t()
        if not k32.ReadProcessMemory(h, ctypes.c_void_p(va), buf, size, ctypes.byref(rd)):
            return b""
        return buf.raw[:rd.value]

    regions = []
    addr = 0
    while addr < 0x7FFF0000:
        mbi = MEMORY_BASIC_INFORMATION()
        if not k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
            break
        if mbi.State == 0x1000 and mbi.Protect & 0xF0 and mbi.RegionSize:
            regions.append((int(mbi.BaseAddress or 0), mbi.RegionSize))
        addr += max(mbi.RegionSize, 1)

    starts = [0x6212C0, 0x637720, 0x802CA0, 0x754840, 0x7E98F0, 0x808650, 0x4FCEE0]
    hits = {s: [] for s in starts}
    for base, size in regions:
        off = 0
        while off < size:
            data = read_mem(base + off, min(8 * 1024 * 1024, size - off))
            if not data:
                break
            for i in range(len(data) - 5):
                if data[i] == 0xE8:
                    rel = int.from_bytes(data[i+1:i+5], "little", signed=True)
                    target = base + off + i + 5 + rel
                    if target in starts:
                        hits[target].append(base + off + i)
            off += len(data)

    md = Cs(CS_ARCH_X86, CS_MODE_32)
    for target in starts:
        print("TARGET", hex(target), "CALLS", len(hits[target]))
        for va in hits[target][:40]:
            blob = read_mem(va - 8, 32)
            print("  CALLER", hex(va))
            for ins in md.disasm(blob, va - 8):
                print("    ", hex(ins.address), ins.mnemonic, ins.op_str)

    k32.TerminateProcess(pi.hProcess, 0)
    k32.CloseHandle(h)
    k32.CloseHandle(pi.hThread)
    k32.CloseHandle(pi.hProcess)
    return 0


if __name__ == "__main__":
    sys.exit(main())
