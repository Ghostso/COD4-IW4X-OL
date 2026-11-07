"""Trace a 32-bit process running RmProbe.exe and report the faulting
instruction address so a crash inside our emitted code can be localised
against the .localrm section (VA 0x10055000..0x10056000)."""
import ctypes
import os
import sys
from ctypes import wintypes

k32 = ctypes.WinDLL("kernel32", use_last_error=True)

DEBUG_ONLY_THIS_PROCESS = 0x00000002
EXCEPTION_DEBUG_EVENT = 1
EXIT_PROCESS_DEBUG_EVENT = 5
CREATE_PROCESS_DEBUG_EVENT = 3
DBG_CONTINUE = 0x00010002
DBG_EXCEPTION_NOT_HANDLED = 0x80010001


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


class EXCEPTION_RECORD(ctypes.Structure):
    _fields_ = [("ExceptionCode", wintypes.DWORD), ("ExceptionFlags", wintypes.DWORD),
                ("ExceptionRecord", ctypes.c_void_p),
                ("ExceptionAddress", ctypes.c_void_p),
                ("NumberParameters", wintypes.DWORD),
                ("ExceptionInformation", ctypes.c_void_p * 15)]


class EXCEPTION_DEBUG_INFO(ctypes.Structure):
    _fields_ = [("ExceptionRecord", EXCEPTION_RECORD), ("dwFirstChance", wintypes.DWORD)]


class DEBUG_EVENT(ctypes.Structure):
    _fields_ = [("dwDebugEventCode", wintypes.DWORD),
                ("dwProcessId", wintypes.DWORD),
                ("dwThreadId", wintypes.DWORD),
                ("u", ctypes.c_byte * 160)]


def main():
    target = os.path.abspath(sys.argv[1])
    here = os.path.dirname(os.path.abspath(__file__))
    probe = os.path.join(here, "probe32", "out", "RmProbe.exe")
    cmd = '"%s" "%s"' % (probe, target)
    print("CMD =", cmd)
    print()

    si = STARTUPINFO()
    si.cb = ctypes.sizeof(si)
    pi = PROCESS_INFORMATION()
    ok = k32.CreateProcessW(None, cmd, None, None, False,
                            DEBUG_ONLY_THIS_PROCESS, None, None,
                            ctypes.byref(si), ctypes.byref(pi))
    if not ok:
        print("CreateProcess failed:", ctypes.get_last_error())
        return

    k32.WaitForDebugEvent.argtypes = [ctypes.POINTER(DEBUG_EVENT), wintypes.DWORD]
    ev = DEBUG_EVENT()
    status = DBG_CONTINUE
    while True:
        if not k32.WaitForDebugEvent(ctypes.byref(ev), 8000):
            print("timeout waiting for debug event (process likely exited)")
            break
        if ev.dwDebugEventCode == EXCEPTION_DEBUG_EVENT:
            info = EXCEPTION_DEBUG_INFO.from_buffer(ev.u)
            code = info.ExceptionRecord.ExceptionCode
            addr = info.ExceptionRecord.ExceptionAddress or 0
            fc = info.dwFirstChance
            if code == 0xC0000005:
                print("ACCESS VIOLATION first_chance=%d at 0x%08X" % (fc, addr))
                if 0x10055000 <= addr < 0x10056000:
                    print("   >>> inside our .localrm section (offset +0x%X)"
                          % (addr - 0x10055000))
                elif 0x10000000 <= addr < 0x10056000:
                    print("   >>> inside iips/LocalRM image (RVA 0x%X)" % (addr - 0x10000000))
                else:
                    print("   >>> outside the image (natively mapped)")
                status = DBG_CONTINUE
            elif code >= 0xC0000000:
                print("EXCEPTION 0x%08X at 0x%08X first_chance=%d" % (code, addr, fc))
                status = DBG_CONTINUE
        elif ev.dwDebugEventCode == EXIT_PROCESS_DEBUG_EVENT:
            print("process exited")
            k32.ContinueDebugEvent(ev.dwProcessId, ev.dwThreadId, status)
            break
        k32.ContinueDebugEvent(ev.dwProcessId, ev.dwThreadId, status)

    k32.CloseHandle(pi.hProcess)
    k32.CloseHandle(pi.hThread)


if __name__ == "__main__":
    main()
