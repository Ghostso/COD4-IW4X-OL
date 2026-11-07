#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prochandles.py -- list named kernel objects (Section / Event / Mutant) held by a process.

Reverse-engineering aid for the CODOL offline hand-off: it shows which named shared
memory ("Section") and synchronisation objects the game opens, i.e. the TCLS-side
objects it expects (TCLS_TASMEMORY_<pid>, TCLS_SHELLMEMORY_<pid>, and any events or
mutexes created by TCLS).

  python prochandles.py <pid> [--filter substr]

Implementation: NtQuerySystemInformation(SystemHandleInformation) -> per-process handles,
PROCESS_DUP_HANDLE + DuplicateHandle + NtQueryObject to fetch each object's name.
Object type indices are resolved at runtime by creating one Event/Mutant/Section of our
own, so only those three types are ever queried (avoids blocking on pipes).
"""

import ctypes
import ctypes.wintypes as wt
import sys

ntdll = ctypes.WinDLL('ntdll')
k32 = ctypes.WinDLL('kernel32', use_last_error=True)

SystemHandleInformation = 16
STATUS_INFO_LENGTH_MISMATCH = 0xC0000004
PROCESS_DUP_HANDLE = 0x0040
DUPLICATE_SAME_ACCESS = 0x00000002


class UNICODE_STRING(ctypes.Structure):
    _fields_ = [('Length', wt.USHORT), ('MaximumLength', wt.USHORT),
                ('Buffer', ctypes.c_void_p)]


class OBJECT_NAME_INFORMATION(ctypes.Structure):
    _fields_ = [('Name', UNICODE_STRING)]


HAS_64BIT = ctypes.sizeof(ctypes.c_void_p) == 8


class HANDLE_ENTRY_EX64(ctypes.Structure):
    _fields_ = [('Object', ctypes.c_void_p), ('UniqueProcessId', ctypes.c_ulonglong),
                ('HandleValue', ctypes.c_ulonglong), ('GrantedAccess', wt.DWORD),
                ('CreatorBackTraceIndex', wt.USHORT), ('ObjectTypeIndex', wt.USHORT),
                ('HandleAttributes', wt.DWORD), ('Reserved', wt.DWORD)]


class HANDLE_ENTRY_EX32(HANDLE_ENTRY_EX64):
    pass


class SYSTEM_HANDLE_INFORMATION_EX64(ctypes.Structure):
    _fields_ = [('NumberOfHandles', ctypes.c_ulonglong),
                ('Reserved', ctypes.c_ulonglong),
                ('Handles', HANDLE_ENTRY_EX64 * 1)]


class SYSTEM_HANDLE_INFORMATION_EX32(ctypes.Structure):
    _fields_ = [('NumberOfHandles', wt.DWORD), ('Reserved', wt.DWORD),
                ('Handles', HANDLE_ENTRY_EX64 * 1)]


ENTRY = HANDLE_ENTRY_EX64
SYSINFO = SYSTEM_HANDLE_INFORMATION_EX64 if HAS_64BIT else SYSTEM_HANDLE_INFORMATION_EX32
ENTRY_OFFSET = 16 if HAS_64BIT else 8
SystemExtendedHandleInformation = 64


def _query_handles():
    size = 1 << 22
    while size < (1 << 27):
        buf = ctypes.create_string_buffer(size)
        ret_len = ctypes.c_ulonglong()
        status = ntdll.NtQuerySystemInformation(SystemExtendedHandleInformation, buf, size,
                                                ctypes.byref(ret_len))
        if status == STATUS_INFO_LENGTH_MISMATCH:
            size = int(ret_len.value) or size * 2
            continue
        if status != 0:
            raise SystemExit('NtQuerySystemInformation failed: 0x%08X' % (status & 0xFFFFFFFF))
        n = int(ctypes.cast(buf, ctypes.POINTER(SYSINFO)).contents.NumberOfHandles)
        arr = (ENTRY * n).from_buffer(buf, ENTRY_OFFSET)
        return list(arr)
    raise SystemExit('handle table too large')


def _own_type_indices():
    """Create one object of each interesting type and find its ObjectTypeIndex."""
    k32.CreateEventW.restype = wt.HANDLE
    k32.CreateEventW.argtypes = [ctypes.c_void_p, wt.BOOL, wt.BOOL, wt.LPCWSTR]
    k32.CreateMutexW.restype = wt.HANDLE
    k32.CreateMutexW.argtypes = [ctypes.c_void_p, wt.BOOL, wt.LPCWSTR]
    k32.CreateFileMappingW.restype = wt.HANDLE
    k32.CreateFileMappingW.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.DWORD,
                                       wt.DWORD, wt.DWORD, wt.LPCWSTR]
    ev = k32.CreateEventW(None, False, False, None)
    mu = k32.CreateMutexW(None, False, None)
    sec = k32.CreateFileMappingW(wt.HANDLE(-1), None, 4, 0, 16, None)
    mine = {ev: 'Event', mu: 'Mutant', sec: 'Section'}
    lut = {}
    pid = k32.GetCurrentProcessId()
    for h in _query_handles():
        if h.UniqueProcessId == pid and h.HandleValue in mine:
            lut[h.ObjectTypeIndex] = mine[h.HandleValue]
    for h in (ev, mu, sec):
        k32.CloseHandle(h)
    return lut


def _name_of(h, handle):
    buf = ctypes.create_string_buffer(1024)
    ln = ntdll.NtQueryObject(wt.HANDLE(handle), 1, buf, ctypes.sizeof(buf), None)
    if ln != 0:
        return None
    obj = ctypes.cast(buf, ctypes.POINTER(OBJECT_NAME_INFORMATION)).contents
    if not obj.Name.Buffer or not obj.Name.Length:
        return None
    return ctypes.wstring_at(obj.Name.Buffer, obj.Name.Length // 2)


def list_named(pid, want_types, filt=None):
    lut = _own_type_indices()
    hproc = k32.OpenProcess(PROCESS_DUP_HANDLE, False, pid)
    if not hproc:
        raise SystemExit('OpenProcess(PROCESS_DUP_HANDLE) failed: %d' % ctypes.get_last_error())
    me = k32.GetCurrentProcess()
    out = []
    try:
        for h in _query_handles():
            if h.UniqueProcessId != pid:
                continue
            tname = lut.get(h.ObjectTypeIndex)
            if tname not in want_types:
                continue
            dup = wt.HANDLE()
            ok = k32.DuplicateHandle(wt.HANDLE(hproc), wt.HANDLE(h.HandleValue), wt.HANDLE(me),
                                     ctypes.byref(dup), 0, False, DUPLICATE_SAME_ACCESS)
            if not ok:
                continue
            try:
                nm = _name_of(me, dup.value)
            finally:
                k32.CloseHandle(dup)
            if nm and (not filt or filt.lower() in nm.lower()):
                out.append((tname, hex(h.HandleValue), nm))
    finally:
        k32.CloseHandle(hproc)
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    pid = int(sys.argv[1])
    filt = None
    if '--filter' in sys.argv:
        filt = sys.argv[sys.argv.index('--filter') + 1]
    rows = list_named(pid, ('Section', 'Event', 'Mutant', 'Semaphore'), filt)
    seen = set()
    for tname, hv, nm in sorted(rows, key=lambda r: (r[0], r[2])):
        key = (tname, nm)
        tag = '' if key not in seen else '  (dup)'
        seen.add(key)
        print('%-9s %-8s %s%s' % (tname, hv, nm, tag))
    print('--- %d named objects' % len(seen))
    return 0


if __name__ == '__main__':
    sys.exit(main())
