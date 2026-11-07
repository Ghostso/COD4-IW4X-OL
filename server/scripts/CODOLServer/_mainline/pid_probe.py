#!/usr/bin/env python3
"""Minimal elevated probe: modules + first memory regions for a target PID."""

import ctypes
import ctypes.wintypes as wt
import json
import sys

k32 = ctypes.WinDLL('kernel32', use_last_error=True)

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ('BaseAddress', ctypes.c_void_p),
        ('AllocationBase', ctypes.c_void_p),
        ('AllocationProtect', wt.DWORD),
        ('RegionSize', ctypes.c_size_t),
        ('State', wt.DWORD),
        ('Protect', wt.DWORD),
        ('Type', wt.DWORD),
    ]


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [
        ('dwSize', wt.DWORD), ('th32ModuleID', wt.DWORD),
        ('th32ProcessID', wt.DWORD), ('GlblcntUsage', wt.DWORD),
        ('ProccntUsage', wt.DWORD), ('modBaseAddr', ctypes.c_void_p),
        ('modBaseSize', wt.DWORD), ('hModule', ctypes.c_void_p),
        ('szModule', wt.WCHAR * 256), ('szExePath', wt.WCHAR * 260),
    ]


k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p,
                               ctypes.POINTER(MEMORY_BASIC_INFORMATION), ctypes.c_size_t]
k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
k32.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
k32.Module32FirstW.argtypes = [wt.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
k32.Module32FirstW.restype = wt.BOOL
k32.Module32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
k32.Module32NextW.restype = wt.BOOL


def main():
    pid = int(sys.argv[1])
    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    print('OpenProcess', h, 'err', ctypes.get_last_error())
    if not h:
        return 1
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    print('snapshot', snap, 'err', ctypes.get_last_error())
    mods = []
    if snap != wt.HANDLE(-1).value:
        me = MODULEENTRY32W()
        me.dwSize = ctypes.sizeof(me)
        ok = k32.Module32FirstW(snap, ctypes.byref(me))
        while ok:
            mods.append((me.szModule, me.szExePath, int(me.modBaseAddr or 0)))
            ok = k32.Module32NextW(snap, ctypes.byref(me))
        k32.CloseHandle(snap)
    print('modules', len(mods))
    for m in mods[:20]:
        print('  %08X %s %s' % (m[2], m[0], m[1]))
    mbi = MEMORY_BASIC_INFORMATION()
    addr = 0
    shown = 0
    total = 0
    while shown < 12 and k32.VirtualQueryEx(h, ctypes.c_void_p(addr),
                                            ctypes.byref(mbi), ctypes.sizeof(mbi)):
        base = int(mbi.BaseAddress or 0)
        size = int(mbi.RegionSize)
        if shown < 12:
            print('  REGION %08X size=%X state=%X protect=%X type=%X'
                  % (base, size, mbi.State, mbi.Protect, mbi.Type))
            shown += 1
        total += 1
        nxt = base + size
        if nxt <= addr:
            break
        addr = nxt
    print('regions_seen', total)
    k32.CloseHandle(h)
    return 0


if __name__ == '__main__':
    sys.exit(main())
