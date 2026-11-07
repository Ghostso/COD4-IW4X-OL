#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
memory_scan.py -- read-only keyword scan of a live 32-bit process.

Used here to inspect the live CODOL client after the engine has initialized:
look for lobby/config/server/ACE strings and loaded anti-cheat modules without
restarting the game. Read-only: no injection, no patching.

Usage:
    python memory_scan.py <pid> --out <dir> [--max-hits 2000]
"""

import argparse
import ctypes
import ctypes.wintypes as wt
import json
import os
import re
import struct
import sys
import time

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
advapi32 = ctypes.WinDLL('advapi32', use_last_error=True)

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
MEM_COMMIT = 0x1000
PAGE_GUARD = 0x100
PAGE_NOACCESS = 0x01

TOKEN_ADJUST_PRIVILEGES = 0x0020
TOKEN_QUERY = 0x0008
SE_PRIVILEGE_ENABLED = 0x00000002
SE_DEBUG_NAME = 'SeDebugPrivilege'

TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010


class LUID(ctypes.Structure):
    _fields_ = [('LowPart', wt.DWORD), ('HighPart', wt.LONG)]


class LUID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [('Luid', LUID), ('Attributes', wt.DWORD)]


class TOKEN_PRIVILEGES(ctypes.Structure):
    _fields_ = [('PrivilegeCount', wt.DWORD),
                ('Privileges', LUID_AND_ATTRIBUTES * 1)]


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
        ('dwSize', wt.DWORD),
        ('th32ModuleID', wt.DWORD),
        ('th32ProcessID', wt.DWORD),
        ('GlblcntUsage', wt.DWORD),
        ('ProccntUsage', wt.DWORD),
        ('modBaseAddr', ctypes.c_void_p),
        ('modBaseSize', wt.DWORD),
        ('hModule', ctypes.c_void_p),
        ('szModule', wt.WCHAR * 256),
        ('szExePath', wt.WCHAR * 260),
    ]


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
k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p,
                               ctypes.POINTER(MEMORY_BASIC_INFORMATION), ctypes.c_size_t]
k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
k32.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
k32.Module32FirstW.argtypes = [wt.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
k32.Module32FirstW.restype = wt.BOOL
k32.Module32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
k32.Module32NextW.restype = wt.BOOL

KEYWORDS = [
    'config_mp.cfg', 'config', 'dvar', 'lobby', 'blaze', 'demonware',
    'dwlobby', 'dw_config', 'party', 'playlist', 'matchmaking', 'master',
    'server', 'host', 'port', 'iips', 'qos', 'stun', 'nfs', 'onlinegame',
    'title_id', 'http://', 'https://', 'tcp', 'udp', 'connect', 'session',
    'ticket', 'auth', 'login', 'account', 'profile', 'tcls', 'wegame',
    'qq.com', 'tencent', 'gcloud', 'ace', 'anticheat', 'anti-cheat',
    'bugtrace', 'tenproxy', 'sguard', 'tguard', 'tp3', 'protect',
]


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


def modules(pid):
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    if snap == wt.HANDLE(-1).value:
        return []
    me = MODULEENTRY32W()
    me.dwSize = ctypes.sizeof(me)
    out = []
    ok = k32.Module32FirstW(snap, ctypes.byref(me))
    while ok:
        out.append({
            'name': me.szModule,
            'path': me.szExePath,
            'base': int(me.modBaseAddr or 0),
            'size': int(me.modBaseSize),
        })
        ok = k32.Module32NextW(snap, ctypes.byref(me))
    k32.CloseHandle(snap)
    return out


def readable_regions(h):
    addr = 0
    mbi = MEMORY_BASIC_INFORMATION()
    while k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi),
                             ctypes.sizeof(mbi)):
        base = int(mbi.BaseAddress or 0)
        size = int(mbi.RegionSize)
        if (mbi.State == MEM_COMMIT and not (mbi.Protect & PAGE_GUARD)
                and (mbi.Protect & 0xFF) != PAGE_NOACCESS):
            yield base, size, int(mbi.Protect), int(mbi.Type)
        nxt = base + size
        if nxt <= addr:
            break
        addr = nxt


def read_some(h, base, size):
    buf = ctypes.create_string_buffer(size)
    got = ctypes.c_size_t()
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(base), buf, size,
                                 ctypes.byref(got)):
        return b''
    return buf.raw[:got.value]


def printable(chunk):
    return ''.join(chr(c) if 32 <= c < 127 else '.' for c in chunk)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pid', type=int)
    ap.add_argument('--out', required=True)
    ap.add_argument('--max-hits', type=int, default=3000)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    ok, err = enable_debug_privilege()
    print('SeDebugPrivilege=%s err=%d' % (ok, err), flush=True)

    mods = modules(args.pid)
    with open(os.path.join(args.out, 'modules.json'), 'w', encoding='utf-8') as fh:
        json.dump(mods, fh, indent=2)
    interesting_mods = [m for m in mods if any(
        k in (m['name'] + ' ' + m['path']).lower()
        for k in ('ace', 'anti', 'protect', 'bug', 'guard', 'ten', 'tp3', 'tqm'))]
    for m in interesting_mods:
        print('MODULE %08X %08X %s' % (m['base'], m['size'], m['path']), flush=True)

    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, args.pid)
    if not h:
        raise SystemExit('OpenProcess failed: %d' % ctypes.get_last_error())

    ascii_pats = [(k, k.encode('ascii')) for k in KEYWORDS]
    utf16_pats = [(k, k.encode('utf-16-le')) for k in KEYWORDS]
    hits = []
    t0 = time.time()
    try:
        for base, size, protect, mtype in readable_regions(h):
            # Keep individual reads bounded; skip enormous free/reserved holes.
            off = 0
            while off < size and len(hits) < args.max_hits:
                want = min(0x100000, size - off)
                data = read_some(h, base + off, want)
                if data:
                    low = data
                    for label, pat in ascii_pats + utf16_pats:
                        enc = 'utf16' if pat[:1] == b'\x00' or b'\x00' in pat[:4] else 'ascii'
                        start = 0
                        while len(hits) < args.max_hits:
                            i = low.find(pat, start)
                            if i < 0:
                                break
                            ctx = low[max(0, i - 48):i + len(pat) + 96]
                            hits.append({
                                'va': base + off + i,
                                'region_base': base,
                                'region_size': size,
                                'protect': protect,
                                'type': mtype,
                                'keyword': label,
                                'encoding': enc,
                                'text': printable(ctx),
                            })
                            start = i + 1
                off += want
            if len(hits) >= args.max_hits:
                break
    finally:
        k32.CloseHandle(h)

    out = os.path.join(args.out, 'hits.jsonl')
    with open(out, 'w', encoding='utf-8') as fh:
        for row in hits:
            fh.write(json.dumps(row, ensure_ascii=False) + '\n')
    print('hits=%d elapsed=%.2fs -> %s' % (len(hits), time.time() - t0, out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
