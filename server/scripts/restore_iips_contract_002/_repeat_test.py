"""Repeat the "V1 observer-style" CreateProcess variant N times and measure lifetime."""
import ctypes, os, subprocess, sys, time
from ctypes import wintypes
k32 = ctypes.WinDLL("kernel32", use_last_error=True)

class STARTUPINFO(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR),
                ("lpDesktop", wintypes.LPWSTR), ("lpTitle", wintypes.LPWSTR),
                ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD),
                ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD),
                ("dwXCountChars", wintypes.DWORD), ("dwYCountChars", wintypes.DWORD),
                ("dwFillAttribute", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("wShowWindow", wintypes.WORD), ("cbReserved2", wintypes.WORD),
                ("lpReserved2", ctypes.c_void_p), ("hStdInput", wintypes.HANDLE),
                ("hStdOutput", wintypes.HANDLE), ("hStdError", wintypes.HANDLE)]
class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE),
                ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD)]
k32.CreateProcessW.restype = wintypes.BOOL

GAME = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "COD OL")
EXE = os.path.join(GAME, "codoMP_client_shipRetail.exe")
cmdline = '"%s" -q' % EXE
limit = float(sys.argv[1]) if len(sys.argv) > 1 else 20.0

for i in range(4):
    subprocess.run("taskkill /f /im codoMP_client_shipRetail.exe", shell=True,
                   capture_output=True)
    time.sleep(1.0)
    si = STARTUPINFO(); si.cb = ctypes.sizeof(STARTUPINFO); pi = PROCESS_INFORMATION()
    ok = k32.CreateProcessW(EXE, ctypes.create_unicode_buffer(cmdline), None, None,
                            False, 0, None, GAME, ctypes.byref(si), ctypes.byref(pi))
    if not ok:
        print("run %d CREATE_FAIL err=%d" % (i, ctypes.get_last_error())); continue
    t0 = time.time(); code = wintypes.DWORD()
    while time.time() - t0 < limit:
        k32.GetExitCodeProcess(pi.hProcess, ctypes.byref(code))
        if code.value != 259: break
        time.sleep(0.05)
    lt = time.time() - t0
    print("run %d pid=%d exited=%-5s lifetime=%.2fs exitcode=0x%08X"
          % (i, pi.dwProcessId, code.value != 259, lt, code.value))
    if code.value == 259: k32.TerminateProcess(pi.hProcess, 0)
    k32.CloseHandle(pi.hProcess); k32.CloseHandle(pi.hThread)
    time.sleep(1.0)
