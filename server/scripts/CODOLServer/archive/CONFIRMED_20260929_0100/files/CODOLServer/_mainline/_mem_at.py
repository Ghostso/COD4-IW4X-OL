#!/usr/bin/env python3
"""Read live process memory at an absolute address (read-only).

Usage:
  python -X utf8 CODOLServer/_mainline/_mem_at.py <pid> <hexaddr> [len]

Uses ctypes ReadProcessMemory; never writes.  Intended for inspecting the
objC URL-source fields found by AboProbe sampling.
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import sys

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010

k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p,
                                  ctypes.c_void_p, ctypes.c_size_t,
                                  ctypes.POINTER(ctypes.c_size_t)]


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: _mem_at.py <pid> <hexaddr> [len]")
        return 2
    pid = int(sys.argv[1])
    addr = int(sys.argv[2], 16)
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 64

    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        print("OpenProcess failed:", ctypes.get_last_error())
        return 2

    buf = ctypes.create_string_buffer(n)
    got = ctypes.c_size_t(0)
    ok = k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, n,
                               ctypes.byref(got))
    print(f"pid={pid} addr=0x{addr:08X} ok={bool(ok)} got={got.value}")
    if not ok:
        print("  err:", ctypes.get_last_error())
        return 1
    raw = buf.raw[:got.value]
    print("  hex:", raw.hex())
    text = "".join(chr(b) if 0x20 <= b < 0x7F else "." for b in raw)
    print("  txt:", text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
