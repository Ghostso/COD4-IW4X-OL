#!/usr/bin/env python3
"""Dump the embedded libcurl handle's status-code candidates (read-only).

The AFD ETW trace proved the objC queue request completed: 834 bytes were
received and TLS closed cleanly.  So the failure is in which field the client
reads, not in transport.  This scans the curl handle for every plausible
RESPONSE_CODE slot so the real one can be identified by which holds 200.

Usage:
  python -X utf8 CODOLServer/_mainline/_curl_probe.py <pid> <curl-handle-hex>
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import struct
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

# Offsets the libcurl 7.38 layout could plausibly use for httpcode, plus the
# slots actually referenced by the client's CURLINFO dispatcher (0xAD4700).
CANDIDATES = [
    0x274, 0x278, 0x27C,
    0x870C, 0x8710, 0x8714, 0x8718, 0x871C, 0x8720, 0x8724, 0x8728, 0x872C,
    0x8730, 0x876C, 0x87A0, 0x86D8, 0x86DC, 0x86E0, 0x85F4,
]


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: _curl_probe.py <pid> <curl-handle-hex>")
        return 2
    pid = int(sys.argv[1])
    handle = int(sys.argv[2], 16)

    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        print("OpenProcess failed:", ctypes.get_last_error())
        return 2

    def rd(addr: int, n: int = 4):
        buf = ctypes.create_string_buffer(n)
        got = ctypes.c_size_t(0)
        ok = k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, n,
                                   ctypes.byref(got))
        if not ok or got.value != n:
            return None
        return buf.raw

    print(f"pid={pid} curl=0x{handle:08X}")
    print("--- RESPONSE_CODE candidates ---")
    for off in CANDIDATES:
        raw = rd(handle + off)
        if raw is None:
            print(f"  +0x{off:04X}  <unreadable>")
            continue
        val = struct.unpack("<I", raw)[0]
        mark = "   <== 200!" if val == 200 else ""
        print(f"  +0x{off:04X}  {val:10d}  0x{val:08X}{mark}")

    # Also show the curl private fields the dispatcher reads, as a sanity map.
    print("--- nearby dwords (context) ---")
    for off in range(0x270, 0x288, 4):
        raw = rd(handle + off)
        if raw is None:
            continue
        val = struct.unpack("<I", raw)[0]
        print(f"  +0x{off:04X}  {val:10d}  0x{val:08X}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
