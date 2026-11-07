"""Run Probe32.exe on a target under a debugger and log every
STATUS_INVALID_IMAGE_FORMAT (0xC000007B) exception plus the faulting
instruction pointer, so we can see exactly which loader validation trips.
"""
import os
import subprocess
import sys

import capstone
from ctypes import windll, byref, c_ulong, c_void_p, WinDLL, Structure, c_int

CBTYPE = {1: "DEBUG_PROCESS", 2: "DEBUG_ONLY_THIS_PROCESS"}

kernel32 = WinDLL("kernel32", use_last_error=True)

CREATE_PROCESS_DEBUG_EVENT = 3
LOAD_DLL_DEBUG_EVENT = 6
UNLOAD_DLL_DEBUG_EVENT = 7
EXCEPTION_DEBUG_EVENT = 1
EXIT_PROCESS_DEBUG_EVENT = 5


class STARTUPINFO(Structure):
    _fields_ = [
        ("cb", c_ulong), ("lpReserved", c_void_p), ("lpDesktop", c_void_p),
        ("lpTitle", c_void_p), ("dwX", c_ulong), ("dwY", c_ulong),
        ("dwXSize", c_ulong), ("dwYSize", c_ulong), ("dwXCountChars", c_ulong),
        ("dwYCountChars", c_ulong), ("dwFillAttribute", c_ulong),
        ("dwFlags", c_ulong), ("wShowWindow", c_int), ("cbReserved2", c_int),
        ("lpReserved2", c_void_p), ("hStdInput", c_void_p),
        ("hStdOutput", c_void_p), ("hStdError", c_void_p),
    ]


class PROCESS_INFORMATION(Structure):
    _fields_ = [("hProcess", c_void_p), ("hThread", c_void_p),
                ("dwProcessId", c_ulong), ("dwThreadId", c_ulong)]


class EXCEPTION_RECORD(Structure):
    _fields_ = [
        ("ExceptionCode", c_ulong), ("ExceptionFlags", c_ulong),
        ("ExceptionRecord", c_void_p), ("ExceptionAddress", c_void_p),
        ("NumberParameters", c_ulong), ("ExceptionInformation", c_void_p * 15),
    ]


class EXCEPTION_DEBUG_INFO(Structure):
    _fields_ = [("ExceptionRecord", EXCEPTION_RECORD), ("dwFirstChance", c_ulong)]


class DEBUG_EVENT(Structure):
    _fields_ = [("dwDebugEventCode", c_ulong), ("dwProcessId", c_ulong),
                ("dwThreadId", c_ulong), ("payload", c_void_p * 20)]


def main():
    if len(sys.argv) < 2:
        print("usage: trace_load.py <target.dll>")
        return
    target = os.path.abspath(sys.argv[1])
    here = os.path.dirname(os.path.abspath(__file__))
    probe = os.path.join(here, "probe32", "out", "Probe32.exe")

    si = STARTUPINFO()
    si.cb = 0x44
    pi = PROCESS_INFORMATION()
    cmd = '"%s" "%s" GetResourceManagerII' % (probe, target)
    print("TRACE_CMD =", cmd)

    CREATE_SUSPENDED = 0x00000004
    DEBUG_PROCESS = 0x00000001
    DEBUG_ONLY_THIS_PROCESS = 0x00000002

    ok = kernel32.CreateProcessW(None, cmd, None, None, False,
                                 DEBUG_ONLY_THIS_PROCESS, None, None,
                                 byref(si), byref(pi))
    if not ok:
        print("CreateProcess failed err=%d" % kernel32.GetLastError())
        return
    print("PID =", pi.dwProcessId)

    h = kernel32.OpenProcess(0x1F0FFF, False, pi.dwProcessId)

    ev = DEBUG_EVENT()
    seen = 0
    continue_status = 0x00010002  # DBG_CONTINUE
    while True:
        if not kernel32.WaitForDebugEvent(byref(ev), 5000):
            err = kernel32.GetLastError()
            if err == 121:  # ERROR_SEM_TIMEOUT
                break
            print("WaitForDebugEvent failed err=%d" % err)
            break
        code = ev.dwDebugEventCode
        pid = ev.dwProcessId
        tid = ev.dwThreadId
        if code == EXCEPTION_DEBUG_EVENT:
            ptr = c_void_p.from_buffer(ev.payload, 0)
            ex = EXCEPTION_DEBUG_INFO.from_buffer(ev.payload)
            ec = ex.ExceptionRecord.ExceptionCode
            addr = ex.ExceptionRecord.ExceptionAddress
            first = ex.dwFirstChance
            if ec in (0xC000007B, 0xC0000135, 0xC0000139, 0xC0000142) or ec >= 0xC0000000:
                print("EXCEPTION code=0x%08X at 0x%08X first_chance=%d"
                      % (ec, addr or 0, first))
                if ec == 0xC000007B:
                    print("  >>> STATUS_INVALID_IMAGE_FORMAT raised here <<<")
                    print("  >>> faulting module base: 0x%08X" % (addr or 0))
            continue_status = 0x00010002  # DBG_CONTINUE
        elif code == EXIT_PROCESS_DEBUG_EVENT:
            exit_code = c_ulong.from_buffer(ev.payload, 0).value
            print("EXIT_PROCESS code=0x%08X (%d)" % (exit_code & 0xFFFFFFFF, exit_code))
            kernel32.ContinueDebugEvent(pid, tid, continue_status)
            break
        seen += 1
        kernel32.ContinueDebugEvent(pid, tid, continue_status)

    print("events seen =", seen)
    kernel32.CloseHandle(pi.hProcess)
    kernel32.CloseHandle(pi.hThread)


if __name__ == "__main__":
    main()
