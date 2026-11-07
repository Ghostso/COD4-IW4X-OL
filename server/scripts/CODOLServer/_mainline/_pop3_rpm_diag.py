# -*- coding: utf-8 -*-
"""
_pop3_rpm_diag.py - why does ReadProcessMemory fail on the game module?

Prints, for a set of module VAs, the result/errno of:
  * ReadProcessMemory at 4 KB and 64 KB granularity
  * NtReadVirtualMemory (the raw syscall underneath)
  * OpenProcess with three access masks
It never writes to the target.

Usage: python -X utf8 _pop3_rpm_diag.py <pid>
"""
import ctypes
import ctypes.wintypes as wt
import sys

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
ntdll = ctypes.WinDLL("ntdll", use_last_error=True)

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
PROCESS_VM_READ = 0x0010
PROCESS_ALL_ACCESS = 0x001F0FFF

k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.CloseHandle.argtypes = [wt.HANDLE]
ntdll.NtReadVirtualMemory.restype = ctypes.c_long
ntdll.NtReadVirtualMemory.argtypes = [wt.HANDLE, ctypes.c_void_p,
                                      ctypes.c_void_p, ctypes.c_size_t,
                                      ctypes.POINTER(ctypes.c_size_t)]

VAS = [0x00401000, 0x00500000, 0x00994000, 0x00CA8000, 0x00E16000, 0x00E19000]
MASKS = [
    (PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, "QUERY|VM_READ"),
    (PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ, "QUERY_LIMITED|VM_READ"),
    (PROCESS_ALL_ACCESS, "ALL_ACCESS"),
]


def rpm(h, va, n):
    buf = ctypes.create_string_buffer(n)
    got = ctypes.c_size_t()
    ctypes.set_last_error(0)
    ok = k32.ReadProcessMemory(h, ctypes.c_void_p(va), buf, n, ctypes.byref(got))
    return bool(ok), ctypes.get_last_error(), got.value, buf.raw[:16]


def ntrpm(h, va, n):
    buf = ctypes.create_string_buffer(n)
    got = ctypes.c_size_t()
    st = ntdll.NtReadVirtualMemory(h, ctypes.c_void_p(va), buf, n, ctypes.byref(got))
    return st, got.value, buf.raw[:16]


def main():
    pid = int(sys.argv[1])
    print("pid=%d" % pid)
    for mask, name in MASKS:
        h = k32.OpenProcess(mask, False, pid)
        err = ctypes.get_last_error()
        print("OpenProcess(%s) -> %s err=%d" % (name, h, err))
        if not h:
            continue
        for va in VAS:
            ok, err, got, first = rpm(h, va, 0x1000)
            print("  RPM 4K   0x%08X ok=%s err=%-5d got=0x%X %s"
                  % (va, ok, err, got, first.hex()))
            ok, err, got, first = rpm(h, va, 0x10000)
            print("  RPM 64K  0x%08X ok=%s err=%-5d got=0x%X" % (va, ok, err, got))
            st, got, first = ntrpm(h, va, 0x1000)
            print("  NtRVM    0x%08X st=0x%08X got=0x%X %s"
                  % (va, st & 0xFFFFFFFF, got, first.hex()))
        k32.CloseHandle(h)
        print("")
    return 0


if __name__ == "__main__":
    sys.exit(main())
