# -*- coding: utf-8 -*-
"""
_po7_memdump.py - live memory forensics for the IN-GAME popup.

Goal: capture the game's OWN memory at the moment the in-game "[100]" panel is
on screen, so the popup's construction can be found.  Nothing is injected, no
code is patched; this only reads.

It waits for codoMP_client_shipRetail.exe, then repeatedly:
  * dumps the whole committed image of the module and of every other private
    region that looks like engine/UI data,
  * greps the dumps for the popup's literal and for the UI keys around it,
  * records the exact tick the window appears.

Usage (must run elevated):
    python -X utf8 _po7_memdump.py --out DIR --seconds 200 --step 3
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
psapi = ctypes.WinDLL('psapi', use_last_error=True)
u32 = ctypes.windll.user32
advapi32 = ctypes.WinDLL('advapi32', use_last_error=True)

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
PROCESS_VM_READ = 0x0010
MEM_COMMIT = 0x1000
PAGE_NOACCESS = 0x01
PAGE_GUARD = 0x100

TOKEN_ADJUST_PRIVILEGES = 0x0020
TOKEN_QUERY = 0x0008
SE_PRIVILEGE_ENABLED = 0x00000002


class MBI(ctypes.Structure):
    _fields_ = [('BaseAddress', ctypes.c_void_p),
                ('AllocationBase', ctypes.c_void_p),
                ('AllocationProtect', wt.DWORD),
                ('Alignment1', wt.DWORD),
                ('RegionSize', ctypes.c_ulonglong),
                ('State', wt.DWORD),
                ('Protect', wt.DWORD),
                ('Type', wt.DWORD),
                ('Alignment2', wt.DWORD)]


k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p,
                               ctypes.POINTER(MBI), ctypes.c_size_t]
k32.OpenProcess.restype = wt.HANDLE
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]

NEEDLES = [
    b'[100]',
    '[100]'.encode('gbk'),
    '[100]'.encode('utf-16-le'),
    b'@SF_UI_DW_LIVE_CONNECTING_FAILED',
    b'DW_LOBBY_ERROR',
    b'DW_LOBBY_CONNECTED',
    b'cppOnDWDisconnected',
    b'cppOnDWConnected',
    b'bdLobbyErrorCode',
    '无法连接大厅服务'.encode('gbk'),
    '确定'.encode('gbk'),
]


def enable_debug():
    advapi32.OpenProcessToken.restype = wt.BOOL
    h = wt.HANDLE()
    if not advapi32.OpenProcessToken(k32.GetCurrentProcess(),
                                     TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY,
                                     ctypes.byref(h)):
        return False

    class LUID(ctypes.Structure):
        _fields_ = [('LowPart', wt.DWORD), ('HighPart', wt.LONG)]

    class LAA(ctypes.Structure):
        _fields_ = [('Luid', LUID), ('Attributes', wt.DWORD)]

    class TP(ctypes.Structure):
        _fields_ = [('PrivilegeCount', wt.DWORD), ('Privileges', LAA * 1)]

    luid = LUID()
    advapi32.LookupPrivilegeValueW(None, 'SeDebugPrivilege', ctypes.byref(luid))
    tp = TP()
    tp.PrivilegeCount = 1
    tp.Privileges[0].Luid = luid
    tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED
    r = advapi32.AdjustTokenPrivileges(h, False, ctypes.byref(tp), 0, None, None)
    return bool(r) and ctypes.get_last_error() == 0


def find_pid():
    arr = (wt.DWORD * 4096)()
    need = wt.DWORD()
    if not psapi.EnumProcesses(ctypes.byref(arr), ctypes.sizeof(arr),
                               ctypes.byref(need)):
        return None
    n = need.value // ctypes.sizeof(wt.DWORD)
    me = k32.GetCurrentProcessId()
    for i in range(n):
        pid = arr[i]
        if pid == 0 or pid == me:
            continue
        h = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not h:
            continue
        buf = ctypes.create_unicode_buffer(1024)
        sz = wt.DWORD(1024)
        ok = k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(sz))
        k32.CloseHandle(h)
        if ok and buf.value.lower().endswith('codomp_client_shipretail.exe'):
            return pid
    return None


def window_visible_for(pid):
    found = []
    EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)

    def cb(h, l):
        if not u32.IsWindowVisible(h):
            return True
        p = wt.DWORD()
        u32.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value != pid:
            return True
        cn = ctypes.create_unicode_buffer(128)
        u32.GetClassNameW(h, cn, 128)
        tl = ctypes.create_unicode_buffer(256)
        u32.GetWindowTextW(h, tl, 256)
        found.append((cn.value, tl.value))
        return True

    u32.EnumWindows(EnumProc(cb), 0)
    return found


def regions(h):
    out = []
    addr = 0
    mbi = MBI()
    limit = 0x7FFFFFFF0000
    while addr < limit:
        got = k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi),
                                 ctypes.sizeof(mbi))
        if not got:
            break
        base = mbi.BaseAddress or 0
        size = mbi.RegionSize
        if size == 0:
            break
        out.append((base, size, mbi.State, mbi.Protect, mbi.Type))
        nxt = base + size
        if nxt <= addr:
            break
        addr = nxt
    return out


def read_region(h, base, size):
    if size > 96 * 1024 * 1024:
        size = 96 * 1024 * 1024
    buf = ctypes.create_string_buffer(size)
    got = ctypes.c_size_t()
    ok = k32.ReadProcessMemory(h, ctypes.c_void_p(base), buf, size,
                               ctypes.byref(got))
    if not ok or got.value == 0:
        return None
    return buf.raw[:got.value]


def scan(blob, base, hits):
    for nd in NEEDLES:
        start = 0
        while True:
            i = blob.find(nd, start)
            if i < 0:
                break
            hits.append({'needle': nd.decode('latin1'), 'va': base + i,
                         'ctx': blob[max(0, i - 24):i + 64].decode(
                             'latin1', 'replace')})
            start = i + 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--seconds', type=float, default=200.0)
    ap.add_argument('--step', type=float, default=3.0)
    ap.add_argument('--pid', type=int, default=0)
    ap.add_argument('--max-region', type=lambda s: int(s, 0),
                    default=0x2000000)
    args = ap.parse_args()

    out = args.out if os.path.isabs(args.out) else os.path.join(
        r'D:\BaiduNetdiskDownload\使命召唤OL', args.out)
    os.makedirs(out, exist_ok=True)
    jsonl = os.path.join(out, 'mem_scan.jsonl')
    log = open(jsonl, 'a', encoding='utf-8')

    dbg = enable_debug()
    print('SeDebugPrivilege=', dbg)
    log.write(json.dumps({'debug': dbg}) + '\n')

    t0 = time.time()
    pid = args.pid
    while pid == 0 and time.time() - t0 < args.seconds:
        pid = find_pid()
        if not pid:
            time.sleep(0.5)
    print('pid=', pid)
    if not pid:
        print('game never appeared')
        return 1

    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        err = ctypes.get_last_error()
        print('OpenProcess failed err=', err)
        # retry with limited
        h = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ,
                            False, pid)
        print('retry limited ->', bool(h), 'err', ctypes.get_last_error())
        if not h:
            return 2

    best = None
    while time.time() - t0 < args.seconds:
        el = round(time.time() - t0, 3)
        wins = window_visible_for(pid)
        rec = {'t': el, 'pid': pid, 'windows': wins}
        regs = regions(h)
        rec['region_count'] = len(regs)
        hits = []
        total = 0
        for base, size, state, protect, typ in regs:
            if state != MEM_COMMIT:
                continue
            if protect & PAGE_NOACCESS or protect & PAGE_GUARD:
                continue
            if size > args.max_region:
                continue
            blob = read_region(h, base, size)
            if not blob:
                continue
            total += len(blob)
            scan(blob, base, hits)
            if len(hits) > 400:
                break
        rec['scanned_bytes'] = total
        rec['hits'] = hits[:200]
        log.write(json.dumps(rec, ensure_ascii=False) + '\n')
        log.flush()
        if hits:
            best = rec
            print('t=%s HITS=%d wins=%s' % (el, len(hits), wins))
            for hh in hits[:8]:
                print('    %-28s @0x%X  %r' % (hh['needle'], hh['va'],
                                               hh['ctx'][:60]))
            # a hit means the popup (or its data) is in memory: dump and stop
            break
        else:
            print('t=%s no hits scanned=%.1fMB wins=%s'
                  % (el, total / 1048576.0, wins))
        time.sleep(args.step)

    if best:
        open(os.path.join(out, 'best_hits.json'), 'w', encoding='utf-8').write(
            json.dumps(best, ensure_ascii=False, indent=2))
        print('wrote best_hits.json')
    k32.CloseHandle(h)
    log.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
