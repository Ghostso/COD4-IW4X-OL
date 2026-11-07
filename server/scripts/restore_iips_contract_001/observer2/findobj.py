"""Locate the object returned by CreateVSDIDrvObj, without a debugger.

Strategy: the factory runs at ~1.7 s (right after VSDDrvDll maps).  Its
return value is stored somewhere in the game's memory, usually on the stack
of the calling thread or in a global.  A pointer INTO the VSDDrvDll module
(range [base, base+size)) is a strong signature.

We scan the game's writable regions for dwords inside that range, both before
and after the factory is known to have run, and report what appears.
"""
import ctypes
import os
import re
import struct
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

K32 = ctypes.WinDLL("kernel32", use_last_error=True)

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
MEM_COMMIT = 0x1000
PAGE_GUARD = 0x100
PAGE_NOACCESS = 0x01


class MBI(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", ctypes.c_ulong),
        ("RegionSize", ctypes.c_size_t),
        ("State", ctypes.c_ulong),
        ("Protect", ctypes.c_ulong),
        ("Type", ctypes.c_ulong),
    ]


def find_pid(name):
    out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"],
                         capture_output=True).stdout.decode("gbk", "replace")
    for line in out.splitlines():
        parts = [p.strip('"') for p in line.split('","')]
        if len(parts) >= 2 and parts[0].lower() == name.lower():
            return int(parts[1])
    return None


def readable_regions(h):
    """Yield (base, size) of committed, readable, non-guard regions."""
    addr = 0
    mbi = MBI()
    while addr < 0x7FFF0000:
        got = K32.VirtualQueryEx(ctypes.c_void_p(h), ctypes.c_void_p(addr),
                                 ctypes.byref(mbi), ctypes.sizeof(mbi))
        if not got:
            addr += 0x1000
            continue
        base = mbi.BaseAddress or 0
        size = mbi.RegionSize
        prot = mbi.Protect
        if (mbi.State == MEM_COMMIT
                and not (prot & PAGE_GUARD)
                and prot not in (PAGE_NOACCESS,)
                and (prot & 0xEE)          # any readable bit
                and size < 0x8000000):
            yield base, size
        addr = base + size


def scan_for_range(h, lo, hi, limit=64):
    """Find dwords whose value lies in [lo,hi)."""
    hits = []
    buf = ctypes.create_string_buffer(0x10000)
    read = ctypes.c_size_t(0)
    for base, size in readable_regions(h):
        off = 0
        while off < size:
            n = min(0x10000, size - off)
            ok = K32.ReadProcessMemory(
                ctypes.c_void_p(h), ctypes.c_void_p(base + off),
                buf, ctypes.c_size_t(n), ctypes.byref(read))
            if ok and read.value >= 4:
                data = buf.raw[:read.value]
                for i in range(0, len(data) - 3, 4):
                    v = struct.unpack_from("<I", data, i)[0]
                    if lo <= v < hi:
                        hits.append((base + off + i, v))
                        if len(hits) >= limit:
                            return hits
            off += n
    return hits


def main():
    pid = find_pid("codoMP_client_shipRetail.exe")
    if pid is None:
        print("game not running")
        return
    h = K32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ,
                        False, pid)
    if not h:
        print("OpenProcess failed:", ctypes.get_last_error())
        return
    print("pid", pid)
    # VSDDrvDll base from the log
    print("scanning for pointers into VSDDrvDll (0x64310000..0x657FC000)")
    hits = scan_for_range(h, 0x64310000, 0x64310000 + 0x14EC000)
    print("found", len(hits))
    for a, v in hits[:32]:
        print("   [0x%08X] = 0x%08X" % (a, v))
    K32.CloseHandle(ctypes.c_void_p(h))


if __name__ == "__main__":
    main()
