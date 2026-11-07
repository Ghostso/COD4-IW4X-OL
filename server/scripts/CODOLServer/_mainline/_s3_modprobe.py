"""S3: list loaded modules of CODOL-related processes (needs elevation).

Usage: python _s3_modprobe.py [pid ...]
With no pids, probes every codoMP_*/IIPSHostApp/TQMCenter process.
"""
import ctypes
import ctypes.wintypes as w
import subprocess
import sys

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
LIST_MODULES_ALL = 0x03

psapi = ctypes.WinDLL("psapi")
k32 = ctypes.WinDLL("kernel32")

psapi.EnumProcessModulesEx.argtypes = [
    w.HANDLE, ctypes.c_void_p, w.DWORD,
    ctypes.POINTER(w.DWORD), w.DWORD,
]
psapi.EnumProcessModulesEx.restype = w.BOOL
psapi.GetModuleFileNameExW.argtypes = [
    w.HANDLE, w.HMODULE, w.LPWSTR, w.DWORD,
]
psapi.GetModuleFileNameExW.restype = w.DWORD
k32.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
k32.OpenProcess.restype = w.HANDLE


def related_pids():
    ps = ("Get-Process | Where-Object {$_.ProcessName -match "
          "'codoMP|IIPSHostApp|TQMCenter|CrossProxy|TGP'} | "
          "ForEach-Object { $_.Id }")
    out = subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps],
                         capture_output=True, text=True)
    return [int(x) for x in out.stdout.split()]


def modules(pid):
    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        return None, ctypes.GetLastError()
    try:
        hmods = (w.HMODULE * 2048)()
        need = w.DWORD()
        if not psapi.EnumProcessModulesEx(h, ctypes.byref(hmods),
                                          ctypes.sizeof(hmods),
                                          ctypes.byref(need), LIST_MODULES_ALL):
            return None, ctypes.GetLastError()
        out = []
        for i in range(need.value // ctypes.sizeof(w.HMODULE)):
            buf = ctypes.create_unicode_buffer(1024)
            psapi.GetModuleFileNameExW(h, hmods[i], buf, 1024)
            out.append(buf.value)
        return out, 0
    finally:
        k32.CloseHandle(h)


def main():
    pids = [int(x) for x in sys.argv[1:]] or related_pids()
    if not pids:
        print("no related processes")
        return 0
    keys = ("iips", "ifs2", "p2papp", "iiipshost", "tenio", "hostapp")
    for pid in pids:
        mods, err = modules(pid)
        if mods is None:
            print("pid=%-6d OpenProcess/Enum failed err=%d" % (pid, err))
            continue
        hits = [m for m in mods if any(k in m.lower() for k in keys)]
        print("pid=%-6d modules=%-4d hits=%d" % (pid, len(mods), len(hits)))
        for m in hits:
            print("    %s" % m)
    return 0


if __name__ == "__main__":
    sys.exit(main())
