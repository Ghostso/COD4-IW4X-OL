#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
engine_early.py -- high-frequency early capture of the CODOL engine fill.

The VM fills the engine gap only during a short window right after process
start, and the region can be released again within a few seconds. This tool
polls a configurable set of probe pages at high frequency and records, for
each poll: the timestamp, per-page non-zero counts and the page protection.
When a page transitions from zero to non-zero it immediately snapshots the
whole useful window.

Read-only: OpenProcess + ReadProcessMemory + VirtualQueryEx only.

Usage:
    python engine_early.py <pid> --out <dir> [--watch-seconds 30] [--step 0.03]
"""

import argparse
import ctypes
import ctypes.wintypes as wt
import json
import os
import struct
import sys
import time

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
advapi32 = ctypes.WinDLL('advapi32', use_last_error=True)

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
PAGE = 0x1000

TOKEN_ADJUST_PRIVILEGES = 0x0020
TOKEN_QUERY = 0x0008
SE_PRIVILEGE_ENABLED = 0x00000002
SE_DEBUG_NAME = 'SeDebugPrivilege'


class LUID(ctypes.Structure):
    _fields_ = [('LowPart', wt.DWORD), ('HighPart', wt.LONG)]


class LUID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [('Luid', LUID), ('Attributes', wt.DWORD)]


class TOKEN_PRIVILEGES(ctypes.Structure):
    _fields_ = [('PrivilegeCount', wt.DWORD),
                ('Privileges', LUID_AND_ATTRIBUTES * 1)]


k32.GetCurrentProcess.restype = wt.HANDLE
advapi32.OpenProcessToken.argtypes = [wt.HANDLE, wt.DWORD,
                                      ctypes.POINTER(wt.HANDLE)]
advapi32.OpenProcessToken.restype = wt.BOOL
advapi32.LookupPrivilegeValueW.argtypes = [wt.LPCWSTR, wt.LPCWSTR,
                                           ctypes.POINTER(LUID)]
advapi32.LookupPrivilegeValueW.restype = wt.BOOL
advapi32.AdjustTokenPrivileges.argtypes = [
    wt.HANDLE, wt.BOOL, ctypes.POINTER(TOKEN_PRIVILEGES), wt.DWORD,
    ctypes.c_void_p, ctypes.POINTER(wt.DWORD)]
advapi32.AdjustTokenPrivileges.restype = wt.BOOL


def enable_debug_privilege():
    token = wt.HANDLE()
    if not advapi32.OpenProcessToken(k32.GetCurrentProcess(),
                                     TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY,
                                     ctypes.byref(token)):
        return False, ctypes.get_last_error()
    luid = LUID()
    if not advapi32.LookupPrivilegeValueW(None, SE_DEBUG_NAME, ctypes.byref(luid)):
        err = ctypes.get_last_error()
        k32.CloseHandle(token)
        return False, err
    tp = TOKEN_PRIVILEGES()
    tp.PrivilegeCount = 1
    tp.Privileges[0].Luid = luid
    tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED
    ctypes.set_last_error(0)
    ok = advapi32.AdjustTokenPrivileges(token, False, ctypes.byref(tp),
                                        ctypes.sizeof(tp), None, None)
    err = ctypes.get_last_error()
    k32.CloseHandle(token)
    return bool(ok) and err == 0, err

WINDOW_BASE = 0x00994000
WINDOW_SIZE = 0x00E65000 - 0x00994000

# Head probes let us detect the fill within milliseconds without reading 5 MB.
PROBES = [
    ('engine_head', 0x00994000, 0x1000),
    ('engine_code', 0x00CA0000, 0x1000),
    ('sentinel', 0x00CA8000, 0x1000),
    ('runtime_strings', 0x00CD0000, 0x1000),
    ('libcurl', 0x00D33000, 0x1000),
]


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


k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p,
                               ctypes.POINTER(MEMORY_BASIC_INFORMATION), ctypes.c_size_t]


def open_pid(pid):
    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        raise SystemExit('OpenProcess(%d) failed: %d (need admin?)'
                         % (pid, ctypes.get_last_error()))
    return h


def read_some(h, base, size):
    buf = ctypes.create_string_buffer(size)
    got = ctypes.c_size_t()
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(base), buf, size,
                                 ctypes.byref(got)):
        return b''
    return buf.raw[:got.value]


def read_window(h, base, size):
    out = bytearray()
    addr = base
    end = base + size
    while addr < end:
        want = min(PAGE, end - addr)
        out += read_some(h, addr, want).ljust(want, b'\x00')
        addr += want
    return bytes(out)


def protect_of(h, addr):
    mbi = MEMORY_BASIC_INFORMATION()
    if k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi),
                          ctypes.sizeof(mbi)):
        return mbi.State, mbi.Protect
    return 0, 0


def derive_runtime_code_range(sentinel):
    if len(sentinel) < 4:
        return None
    vals = list(struct.unpack_from('<%dI' % (len(sentinel) // 4), sentinel, 0))
    highs = [v for v in vals if 0x10000000 <= v < 0x14000000]
    if not highs:
        return None
    base = min(highs) & ~0xFFF
    end = (max(highs) + 0xFFF) & ~0xFFF
    size = end - base
    if size <= 0 or size > 0x100000:
        return None
    return base, size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pid', type=int)
    ap.add_argument('--out', required=True)
    ap.add_argument('--watch-seconds', type=float, default=30.0)
    ap.add_argument('--step', type=float, default=0.03)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    trace = open(os.path.join(args.out, 'early_trace.jsonl'), 'w', encoding='utf-8')
    log = open(os.path.join(args.out, 'early.log'), 'w', encoding='utf-8')

    def say(line):
        log.write(line + '\n')
        log.flush()
        print(line, flush=True)

    dbg_ok, dbg_err = enable_debug_privilege()
    print('SeDebugPrivilege=%s err=%d' % (dbg_ok, dbg_err), flush=True)
    h = open_pid(args.pid)
    try:
        t0 = time.time()
        say('pid=%d watching %d probes for %.1fs at %.0fms step'
            % (args.pid, len(PROBES), args.watch_seconds, args.step * 1000))
        first_fill = None
        snapshots = 0
        while time.time() - t0 < args.watch_seconds:
            row = {'t': round(time.time() - t0, 4)}
            for name, base, size in PROBES:
                data = read_some(h, base, size)
                st, pr = protect_of(h, base)
                row[name] = {'nz': sum(1 for b in data if b),
                             'got': len(data), 'state': st, 'protect': pr}
            trace.write(json.dumps(row) + '\n')
            trace.flush()

            head_nz = row['engine_head']['nz']
            sent_nz = row['sentinel']['nz']
            if first_fill is None and head_nz > 0:
                first_fill = row['t']
                say('t=%.3fs FIRST FILL head_nz=%d sentinel_nz=%d'
                    % (row['t'], head_nz, sent_nz))

            # Snapshot the full window as soon as the head is populated.
            if head_nz > 0 and snapshots < 6:
                win = read_window(h, WINDOW_BASE, WINDOW_SIZE)
                p = os.path.join(args.out, 'window_t%07.3fs.bin' % row['t'])
                with open(p, 'wb') as fh:
                    fh.write(win)
                say('  snapshot %s nonzero=%d' % (os.path.basename(p),
                                                  sum(1 for b in win if b)))
                sentinel = read_window(h, 0x00CA8000, 0x1000)
                with open(os.path.join(args.out, 'sentinel_table.bin'), 'wb') as fh:
                    fh.write(sentinel)
                target = derive_runtime_code_range(sentinel)
                if target:
                    cb, cs = target
                    code = read_window(h, cb, cs)
                    with open(os.path.join(args.out, 'runtime_code.bin'), 'wb') as fh:
                        fh.write(code)
                    with open(os.path.join(args.out, 'runtime_target_range.json'),
                              'w', encoding='utf-8') as fh:
                        json.dump({'base': cb, 'size': cs,
                                   'nonzero': sum(1 for b in code if b),
                                   't': row['t']}, fh, indent=2)
                    say('  RUNTIME_CODE base=0x%08X size=0x%X nonzero=%d'
                        % (cb, cs, sum(1 for b in code if b)))
                snapshots += 1

            # Stop early once the head goes back to zero after having filled.
            if first_fill is not None and head_nz == 0:
                say('t=%.3fs engine head released (zero again)' % row['t'])
                break
            time.sleep(args.step)
        say('done first_fill=%s snapshots=%d' % (first_fill, snapshots))
    finally:
        k32.CloseHandle(h)
        trace.close()
        log.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
