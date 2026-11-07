#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only open/read of the TCLS named shared mapping.

Tries a list of candidate mapping names derived from PIDs of the live CODOL
process tree. No process injection, no writes, no network changes.
"""

import ctypes
import ctypes.wintypes as wt
import json
import os
import struct
import sys

FILE_MAP_READ = 0x0004

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
k32.OpenFileMappingW.restype = wt.HANDLE
k32.OpenFileMappingW.argtypes = [wt.DWORD, wt.BOOL, wt.LPCWSTR]
k32.MapViewOfFile.restype = ctypes.c_void_p
k32.MapViewOfFile.argtypes = [wt.HANDLE, wt.DWORD, wt.DWORD, wt.DWORD,
                              ctypes.c_size_t]
k32.UnmapViewOfFile.argtypes = [ctypes.c_void_p]
k32.CloseHandle.argtypes = [wt.HANDLE]


def pids_from_registry():
    out = []
    # WMI-free: parse tasklist output
    try:
        import subprocess
        out_s = subprocess.check_output(
            ['tasklist', '/fo', 'csv', '/nh'], shell=False)
        for line in out_s.decode('gbk', 'replace').splitlines():
            for name in ('codoMP_client_shipRetail', 'IIPSHostApp',
                         'TQMCenter', 'tcls_core'):
                if '"%s"' % name in line or name in line:
                    cols = [c.strip('"') for c in line.split('","')]
                    try:
                        out.append(int(cols[1]))
                    except (ValueError, IndexError):
                        pass
    except Exception as e:
        print('tasklist failed:', e)
    return sorted(set(out))


def try_name(name):
    h = k32.OpenFileMappingW(FILE_MAP_READ, False, name)
    if not h:
        return None, ctypes.get_last_error()
    view = k32.MapViewOfFile(h, FILE_MAP_READ, 0, 0, 0)
    if not view:
        err = ctypes.get_last_error()
        k32.CloseHandle(h)
        return None, err
    buf = ctypes.string_at(view, 1964)
    k32.UnmapViewOfFile(view)
    k32.CloseHandle(h)
    return buf, 0


def main():
    names = []
    for pid in pids_from_registry():
        for n in ('TCLS_SHAREDMEMEMORY%d' % pid,
                  r'Local\TCLS_SHAREDMEMEMORY%d' % pid,
                  r'Global\TCLS_SHAREDMEMEMORY%d' % pid):
            names.append(n)
    # also allow explicit names from argv
    names += sys.argv[1:]

    print('PIDs:', pids_from_registry())
    found = 0
    for n in names:
        buf, err = try_name(n)
        if buf is None:
            print('MISS %-45s err=%d' % (n, err))
            continue
        found += 1
        print('HIT  %-45s len=%d' % (n, len(buf)))
        for off in range(0, len(buf), 16):
            row = buf[off:off + 16]
            print('  %04X  %-47s  %s' % (
                off, ' '.join('%02x' % c for c in row),
                ''.join(chr(c) if 32 <= c < 127 else '.' for c in row)))
        outp = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            '_tcls_shm_%s.bin' % n.replace('\\', '_'))
        open(outp, 'wb').write(buf)
        print('  saved', outp)
    print('found', found)


if __name__ == '__main__':
    main()
