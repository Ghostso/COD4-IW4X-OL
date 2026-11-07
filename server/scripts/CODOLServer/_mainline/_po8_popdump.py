# -*- coding: utf-8 -*-
"""
_po8_popdump.py - read the game's memory at the moment the IN-GAME popup shows.

Why this file exists: attaching to a running codoMP_client_shipRetail.exe with
ReadProcessMemory is denied by ACE (err=5).  The one path that works is the
one suspend_host_redirect.py already proved: launch the game CREATE_SUSPENDED
and grab a PROCESS_ALL_ACCESS handle BEFORE ACE arms itself, then keep that
handle for the whole session.

This tool does exactly that and nothing else.  It does NOT redirect hosts, does
NOT create listeners, does NOT write to the target.  It only:

  1. launches the game suspended, grabs the pre-ACE handle, resumes it,
  2. starts an independent watcher that polls the screen for the popup and
     writes a marker file the instant it appears / disappears,
  3. repeatedly dumps the whole image and greps it for the popup's fingerprints
     (`[100]`, the DW_LOBBY_* / cppOnDW* symbols, the localization key and its
     Chinese text),
  4. timestamps every hit so the popup's onset can be matched to the first
     moment its data appears in memory.

Run it ELEVATED.

Usage:
    python -X utf8 _po8_popdump.py --out DIR --seconds 160
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import json
import os
import struct
import subprocess
import sys
import threading
import time

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
advapi32 = ctypes.WinDLL('advapi32', use_last_error=True)
u32 = ctypes.windll.user32
g32 = ctypes.windll.gdi32

PROCESS_ALL_ACCESS = 0x001F0FFF
CREATE_SUSPENDED = 0x00000004
MEM_COMMIT = 0x1000
PAGE_GUARD = 0x100
PAGE_NOACCESS = 0x01
SRCCOPY = 0x00CC0020

TOKEN_ADJUST_PRIVILEGES = 0x0020
TOKEN_QUERY = 0x0008
SE_PRIVILEGE_ENABLED = 0x00000002
SE_DEBUG_NAME = 'SeDebugPrivilege'

ROOT = r'D:\BaiduNetdiskDownload\使命召唤OL'


class LUID(ctypes.Structure):
    _fields_ = [('LowPart', wt.DWORD), ('HighPart', wt.LONG)]


class LUID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [('Luid', LUID), ('Attributes', wt.DWORD)]


class TOKEN_PRIVILEGES(ctypes.Structure):
    _fields_ = [('PrivilegeCount', wt.DWORD),
                ('Privileges', LUID_AND_ATTRIBUTES * 1)]


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [('cb', wt.DWORD), ('lpReserved', wt.LPWSTR),
                ('lpDesktop', wt.LPWSTR), ('lpTitle', wt.LPWSTR),
                ('dwX', wt.DWORD), ('dwY', wt.DWORD),
                ('dwXSize', wt.DWORD), ('dwYSize', wt.DWORD),
                ('dwXCountChars', wt.DWORD), ('dwYCountChars', wt.DWORD),
                ('dwFillAttribute', wt.DWORD), ('dwFlags', wt.DWORD),
                ('wShowWindow', wt.WORD), ('cbReserved2', wt.WORD),
                ('lpReserved2', ctypes.c_void_p),
                ('hStdInput', wt.HANDLE), ('hStdOutput', wt.HANDLE),
                ('hStdError', wt.HANDLE)]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [('hProcess', wt.HANDLE), ('hThread', wt.HANDLE),
                ('dwProcessId', wt.DWORD), ('dwThreadId', wt.DWORD)]


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
k32.CreateProcessW.restype = wt.BOOL
k32.CreateProcessW.argtypes = [wt.LPCWSTR, wt.LPWSTR, ctypes.c_void_p,
                               ctypes.c_void_p, wt.BOOL, wt.DWORD,
                               ctypes.c_void_p, wt.LPCWSTR, ctypes.c_void_p,
                               ctypes.c_void_p]
k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.ResumeThread.argtypes = [wt.HANDLE]
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p,
                                  ctypes.c_void_p, ctypes.c_size_t,
                                  ctypes.POINTER(ctypes.c_size_t)]
k32.QueryFullProcessImageNameW.argtypes = [wt.HANDLE, wt.DWORD,
                                           wt.LPWSTR,
                                           ctypes.POINTER(wt.DWORD)]

NEEDLES = [
    b'[100]',
    '[100]'.encode('gbk'),
    '[100]'.encode('utf-16-le'),
    b'@SF_UI_DW_LIVE_CONNECTING_FAILED',
    '无法连接大厅服务'.encode('gbk'),
    b'DW_LOBBY_ERROR',
    b'DW_LOBBY_CONNECTED',
    b'DWLOBBY_PUMP_SUCCESS',
    b'DWLOBBY_PUMP_DISCONNECTED',
    b'cppOnDWDisconnected',
    b'cppOnDWConnected',
    b'bdLobbyErrorCode',
    b'Unknown bdLobbyErrorCode',
    b'dwLogonStart',
    '确定'.encode('gbk'),
]


def enable_debug():
    token = wt.HANDLE()
    if not advapi32.OpenProcessToken(k32.GetCurrentProcess(),
                                     TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY,
                                     ctypes.byref(token)):
        return False, ctypes.get_last_error()
    luid = LUID()
    if not advapi32.LookupPrivilegeValueW(None, SE_DEBUG_NAME,
                                          ctypes.byref(luid)):
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


def regions(h):
    addr = 0
    mbi = MBI()
    while k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi),
                             ctypes.sizeof(mbi)):
        base = int(mbi.BaseAddress or 0)
        size = int(mbi.RegionSize)
        if (mbi.State == MEM_COMMIT and not (mbi.Protect & PAGE_GUARD)
                and (mbi.Protect & 0xFF) != PAGE_NOACCESS):
            yield base, size
        nxt = base + size
        if nxt <= addr:
            return
        addr = nxt


def read_some(h, base, size):
    buf = ctypes.create_string_buffer(size)
    got = ctypes.c_size_t()
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(base), buf, size,
                                 ctypes.byref(got)):
        return b''
    return buf.raw[:got.value]


def scan_blob(blob, base, hits, cap=300):
    for nd in NEEDLES:
        start = 0
        while len(hits) < cap:
            i = blob.find(nd, start)
            if i < 0:
                break
            va = base + i
            hits.append({
                'needle': nd.decode('latin1'),
                'va': va,
                'ctx': blob[max(0, i - 32):i + 96].decode('latin1', 'replace'),
            })
            start = i + 1


# ---------------------------------------------------------------- popup watch
class PanelWatcher(object):
    """Pixel watcher for the in-game panel; writes a marker file on transitions.

    Screen grab needs no elevation, but the window must not be occluded, so the
    caller is expected to run inside a session where the game is foreground.
    """

    def __init__(self, marker_path):
        self.marker = marker_path
        self.w = u32.GetSystemMetrics(0)
        self.h = u32.GetSystemMetrics(1)
        self.screen = u32.GetDC(0)
        self.mem = g32.CreateCompatibleDC(self.screen)
        self.bmp = g32.CreateCompatibleBitmap(self.screen, self.w, self.h)
        g32.SelectObject(self.mem, self.bmp)
        self.bufsz = self.w * self.h * 4
        self.buf = ctypes.create_string_buffer(self.bufsz)
        self.prev = False

    def grab(self):
        if not g32.BitBlt(self.mem, 0, 0, self.w, self.h, self.screen, 0, 0,
                          SRCCOPY):
            return None

        class BMI(ctypes.Structure):
            _fields_ = [('biSize', wt.DWORD), ('biWidth', ctypes.c_long),
                        ('biHeight', ctypes.c_long), ('biPlanes', wt.WORD),
                        ('biBitCount', wt.WORD), ('biCompression', wt.DWORD),
                        ('biSizeImage', wt.DWORD),
                        ('biXPelsPerMeter', ctypes.c_long),
                        ('biYPelsPerMeter', ctypes.c_long),
                        ('biClrUsed', wt.DWORD), ('biClrImportant', wt.DWORD)]

        bi = BMI()
        bi.biSize = ctypes.sizeof(BMI)
        bi.biWidth = self.w
        bi.biHeight = -self.h
        bi.biPlanes = 1
        bi.biBitCount = 32
        g32.GetDIBits(self.mem, self.bmp, 0, self.h, self.buf,
                      ctypes.byref(bi), 0)
        return self.buf.raw

    def score(self, px):
        total = 0
        for y in range(0, self.h, 2):
            b0 = y * self.w * 4
            for x in range(0, self.w, 2):
                o = b0 + x * 4
                b = px[o]
                g = px[o + 1]
                r = px[o + 2]
                if b > 120 and g > 90 and r < b - 30 and g < b + 20:
                    total += 1
        return total

    def run(self, stop_evt, owner_pid):
        with open(self.marker, 'a', encoding='utf-8') as fh:
            fh.write(json.dumps({'t': 0.0, 'event': 'watcher_start'}) + '\n')
            fh.flush()
            t0 = time.time()
            while not stop_evt.is_set():
                px = self.grab()
                if px:
                    sc = self.score(px)
                    hit = sc > 3000
                    if hit != self.prev:
                        fh.write(json.dumps({
                            't': round(time.time() - t0, 3),
                            'event': 'PANEL_APPEAR' if hit else 'PANEL_CLEAR',
                            'score': sc}) + '\n')
                        fh.flush()
                    self.prev = hit
                time.sleep(1.5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--seconds', type=float, default=160.0)
    ap.add_argument('--step', type=float, default=3.0)
    ap.add_argument('--exe', default='')
    ap.add_argument('--cwd', default='')
    ap.add_argument('--watch-panel', type=int, default=1)
    args = ap.parse_args()

    out = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
    os.makedirs(out, exist_ok=True)
    log = open(os.path.join(out, 'popdump.jsonl'), 'w', encoding='utf-8')

    def say(msg, obj=None):
        print(msg, flush=True)
        rec = {'msg': msg}
        if obj:
            rec.update(obj)
        log.write(json.dumps(rec, ensure_ascii=False) + '\n')
        log.flush()

    exe = args.exe or os.path.join(
        ROOT, 'run_codol_001', 'sandbox_ifs1_20260923',
        'codoMP_client_shipRetail.exe')
    cwd = args.cwd or os.path.dirname(exe)

    ok, err = enable_debug()
    say('SeDebugPrivilege=%s err=%d' % (ok, err))

    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(si)
    pi = PROCESS_INFORMATION()
    cmd = '"%s" -q --disable-gpu --disable-gpu-compositing' % exe
    buf = ctypes.create_unicode_buffer(cmd)
    if not k32.CreateProcessW(exe, buf, None, None, True, CREATE_SUSPENDED,
                              None, cwd, ctypes.byref(si), ctypes.byref(pi)):
        say('CreateProcess failed err=%d' % ctypes.get_last_error())
        return 1
    pid = pi.dwProcessId
    say('created suspended pid=%d' % pid)

    h = k32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    say('pre-arm OpenProcess(ALL_ACCESS) -> %s err=%d'
        % (h, ctypes.get_last_error()))
    if not h:
        k32.ResumeThread(pi.hThread)
        return 2

    stop_evt = threading.Event()
    if args.watch_panel:
        w = PanelWatcher(os.path.join(out, 'panel_marker.jsonl'))
        threading.Thread(target=w.run, args=(stop_evt, pid), daemon=True).start()
        say('panel watcher started')

    k32.ResumeThread(pi.hThread)
    say('resumed')

    t0 = time.time()
    first_hit_t = None
    n = 0
    while time.time() - t0 < args.seconds:
        el = round(time.time() - t0, 3)
        n += 1
        blob = bytearray(0x00E65000 - 0x00400000)
        scanned = 0
        for base, size in regions(h):
            a = max(base, 0x00400000)
            b = min(base + size, 0x00E65000)
            if b <= a:
                continue
            data = read_some(h, a, b - a)
            if data:
                blob[a - 0x00400000:a - 0x00400000 + len(data)] = data
                scanned += len(data)
        hits = []
        scan_blob(bytes(blob), 0x00400000, hits)
        if hits and first_hit_t is None:
            first_hit_t = el
        say('t=%.2f scanned=%.1fMB hits=%d' % (el, scanned / 1048576.0, len(hits)),
            {'t': el, 'hits': hits, 'scanned': scanned})
        if hits and n <= 400:
            for hh in hits[:10]:
                print('    %-30s @0x%08X  %r'
                      % (hh['needle'], hh['va'], hh['ctx'][:70]))
        time.sleep(args.step)

    stop_evt.set()
    say('first_hit_t=%s' % first_hit_t)
    k32.CloseHandle(h)
    log.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
