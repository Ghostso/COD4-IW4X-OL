#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
early_handle_scan.py -- create the game suspended, grab the read handle before
ACE can arm, then scan memory as soon as it is populated.

This must run elevated. It:
  1. CreateProcess(game, CREATE_SUSPENDED)
  2. OpenProcess(PROCESS_VM_READ) BEFORE resuming  -> handle survives ACE arming
  3. ResumeThread, poll the engine gap
  4. On first non-zero, scan the whole process for keywords and dump regions

Usage:
    python early_handle_scan.py --exe <game.exe> --cwd <dir> --out <dir>
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
CREATE_SUSPENDED = 0x00000004
MEM_COMMIT = 0x1000
PAGE_GUARD = 0x100
PAGE_NOACCESS = 0x01
ENGINE_BASE = 0x00994000

TOKEN_ADJUST_PRIVILEGES = 0x0020
TOKEN_QUERY = 0x0008
SE_PRIVILEGE_ENABLED = 0x00000002
SE_DEBUG_NAME = 'SeDebugPrivilege'


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [('cb', wt.DWORD), ('lpReserved', wt.LPWSTR), ('lpDesktop', wt.LPWSTR),
                ('lpTitle', wt.LPWSTR), ('dwX', wt.DWORD), ('dwY', wt.DWORD),
                ('dwXSize', wt.DWORD), ('dwYSize', wt.DWORD),
                ('dwXCountChars', wt.DWORD), ('dwYCountChars', wt.DWORD),
                ('dwFillAttribute', wt.DWORD), ('dwFlags', wt.DWORD),
                ('wShowWindow', wt.WORD), ('cbReserved2', wt.WORD),
                ('lpReserved2', ctypes.c_void_p), ('hStdInput', wt.HANDLE),
                ('hStdOutput', wt.HANDLE), ('hStdError', wt.HANDLE)]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [('hProcess', wt.HANDLE), ('hThread', wt.HANDLE),
                ('dwProcessId', wt.DWORD), ('dwThreadId', wt.DWORD)]


class MBI(ctypes.Structure):
    _fields_ = [('BaseAddress', ctypes.c_void_p), ('AllocationBase', ctypes.c_void_p),
                ('AllocationProtect', wt.DWORD), ('RegionSize', ctypes.c_size_t),
                ('State', wt.DWORD), ('Protect', wt.DWORD), ('Type', wt.DWORD)]


class LUID(ctypes.Structure):
    _fields_ = [('LowPart', wt.DWORD), ('HighPart', wt.LONG)]


class LUID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [('Luid', LUID), ('Attributes', wt.DWORD)]


class TOKEN_PRIVILEGES(ctypes.Structure):
    _fields_ = [('PrivilegeCount', wt.DWORD),
                ('Privileges', LUID_AND_ATTRIBUTES * 1)]


k32.GetCurrentProcess.restype = wt.HANDLE
advapi32.OpenProcessToken.argtypes = [wt.HANDLE, wt.DWORD, ctypes.POINTER(wt.HANDLE)]
advapi32.OpenProcessToken.restype = wt.BOOL
advapi32.LookupPrivilegeValueW.argtypes = [wt.LPCWSTR, wt.LPCWSTR,
                                           ctypes.POINTER(LUID)]
advapi32.LookupPrivilegeValueW.restype = wt.BOOL
advapi32.AdjustTokenPrivileges.argtypes = [wt.HANDLE, wt.BOOL,
                                           ctypes.POINTER(TOKEN_PRIVILEGES),
                                           wt.DWORD, ctypes.c_void_p,
                                           ctypes.POINTER(wt.DWORD)]
advapi32.AdjustTokenPrivileges.restype = wt.BOOL
k32.CreateProcessW.restype = wt.BOOL
k32.CreateProcessW.argtypes = [wt.LPCWSTR, wt.LPWSTR, ctypes.c_void_p,
                               ctypes.c_void_p, wt.BOOL, wt.DWORD, ctypes.c_void_p,
                               wt.LPCWSTR, ctypes.c_void_p, ctypes.c_void_p]
k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.POINTER(MBI),
                               ctypes.c_size_t]
k32.ResumeThread.argtypes = [wt.HANDLE]

KEYWORDS = ['config_mp.cfg', 'config', 'dvar', 'lobby', 'blaze', 'demonware',
            'dwlobby', 'party', 'playlist', 'matchmaking', 'master', 'server',
            'host', 'port', 'iips', 'qos', 'stun', 'nfs', 'onlinegame',
            'title_id', 'http://', 'https://', 'connect', 'session', 'ticket',
            'auth', 'login', 'account', 'profile', 'tcls', 'wegame', 'qq.com',
            'tencent', 'ace', 'anticheat', 'bugtrace', 'tenproxy', 'tp3']


def enable_debug():
    token = wt.HANDLE()
    if not advapi32.OpenProcessToken(k32.GetCurrentProcess(),
                                     TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY,
                                     ctypes.byref(token)):
        return False, ctypes.get_last_error()
    luid = LUID()
    if not advapi32.LookupPrivilegeValueW(None, SE_DEBUG_NAME, ctypes.byref(luid)):
        return False, ctypes.get_last_error()
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


def read_some(h, base, size):
    buf = ctypes.create_string_buffer(size)
    got = ctypes.c_size_t()
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(base), buf, size,
                                 ctypes.byref(got)):
        return b''
    return buf.raw[:got.value]


def regions(h):
    addr = 0
    mbi = MBI()
    while k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi),
                             ctypes.sizeof(mbi)):
        base = int(mbi.BaseAddress or 0)
        size = int(mbi.RegionSize)
        if (mbi.State == MEM_COMMIT and not (mbi.Protect & PAGE_GUARD)
                and (mbi.Protect & 0xFF) != PAGE_NOACCESS):
            yield base, size, int(mbi.Protect)
        nxt = base + size
        if nxt <= addr:
            return
        addr = nxt


def scan(h, log, max_hits=4000):
    hits = []
    pats = [(k, k.encode('ascii')) for k in KEYWORDS]
    for base, size, protect in regions(h):
        off = 0
        while off < size and len(hits) < max_hits:
            want = min(0x100000, size - off)
            data = read_some(h, base + off, want)
            if data:
                for label, pat in pats:
                    start = 0
                    while len(hits) < max_hits:
                        i = data.find(pat, start)
                        if i < 0:
                            break
                        ctx = data[max(0, i - 40):i + len(pat) + 80]
                        text = ''.join(chr(c) if 32 <= c < 127 else '.' for c in ctx)
                        hits.append({'va': base + off + i, 'kw': label,
                                     'protect': protect, 'text': text})
                        start = i + 1
            off += want
    log('hits=%d' % len(hits))
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--exe', required=True)
    ap.add_argument('--cwd', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--watch', type=float, default=40.0)
    ap.add_argument('--step', type=float, default=0.05)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    logf = open(os.path.join(args.out, 'early_handle.log'), 'w', encoding='utf-8')

    def log(msg):
        logf.write(msg + '\n')
        logf.flush()
        print(msg, flush=True)

    ok, err = enable_debug()
    log('SeDebugPrivilege=%s err=%d' % (ok, err))

    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(si)
    pi = PROCESS_INFORMATION()
    cmd = '"%s" -q --disable-gpu --disable-gpu-compositing' % args.exe
    buf = ctypes.create_unicode_buffer(cmd)
    created = k32.CreateProcessW(args.exe, buf, None, None, True,
                                 CREATE_SUSPENDED, None, args.cwd,
                                 ctypes.byref(si), ctypes.byref(pi))
    if not created:
        raise SystemExit('CreateProcess failed: %d' % ctypes.get_last_error())
    pid = pi.dwProcessId
    log('created suspended pid=%d' % pid)

    # Grab the read handle while the process is still suspended.
    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    log('pre-arm OpenProcess -> %s err=%d' % (h, ctypes.get_last_error()))

    k32.ResumeThread(pi.hThread)
    log('resumed')

    t0 = time.time()
    filled = None
    while time.time() - t0 < args.watch:
        probe = read_some(h, ENGINE_BASE, 0x1000)
        if probe and any(probe):
            filled = time.time() - t0
            log('engine filled at t=%.2fs' % filled)
            break
        time.sleep(args.step)
    if filled is None:
        log('engine never filled within %.1fs' % args.watch)

    hits = scan(h, log)
    with open(os.path.join(args.out, 'hits.jsonl'), 'w', encoding='utf-8') as fh:
        for row in hits:
            fh.write(json.dumps(row, ensure_ascii=False) + '\n')
    log('done pid=%d hits=%d' % (pid, len(hits)))
    logf.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
