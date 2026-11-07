#!/usr/bin/env python3
"""Elevated read test: how many committed regions can actually be read.""" 

import ctypes
import ctypes.wintypes as wt
import sys

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
MEM_COMMIT = 0x1000
PAGE_GUARD = 0x100
PAGE_NOACCESS = 0x01


class MBI(ctypes.Structure):
    _fields_ = [('BaseAddress', ctypes.c_void_p),
                ('AllocationBase', ctypes.c_void_p),
                ('AllocationProtect', wt.DWORD),
                ('RegionSize', ctypes.c_size_t),
                ('State', wt.DWORD), ('Protect', wt.DWORD), ('Type', wt.DWORD)]


k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.POINTER(MBI),
                               ctypes.c_size_t]


def main():
    pid = int(sys.argv[1])
    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    print('OpenProcess', h, 'err', ctypes.get_last_error())
    if not h:
        return 1
    addr = 0
    mbi = MBI()
    committed = 0
    readable = 0
    shown = 0
    while k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi),
                             ctypes.sizeof(mbi)):
        base = int(mbi.BaseAddress or 0)
        size = int(mbi.RegionSize)
        if mbi.State == MEM_COMMIT and not (mbi.Protect & PAGE_GUARD) and (mbi.Protect & 0xFF) != PAGE_NOACCESS:
            committed += 1
            buf = ctypes.create_string_buffer(min(size, 4096))
            got = ctypes.c_size_t()
            ok = k32.ReadProcessMemory(h, ctypes.c_void_p(base), buf,
                                       len(buf), ctypes.byref(got))
            if ok and got.value:
                readable += 1
                if shown < 20:
                    print('READ_OK %08X size=%X got=%X first=%s' %
                          (base, size, got.value, buf.raw[:16].hex()))
                    shown += 1
            elif shown < 20:
                print('READ_FAIL %08X size=%X protect=%X err=%d' %
                      (base, size, mbi.Protect, ctypes.get_last_error()))
                shown += 1
        nxt = base + size
        if nxt <= addr:
            break
        addr = nxt
    print('committed=%d readable=%d' % (committed, readable))
    k32.CloseHandle(h)
    return 0


if __name__ == '__main__':
    sys.exit(main())
