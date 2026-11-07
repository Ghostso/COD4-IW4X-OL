#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
procmem.py -- small live-process helper (32/64-bit aware, uses ReadProcessMemory).

  python procmem.py modules <pid>
  python procmem.py windows <pid>
  python procmem.py scan <pid> ascii <text> [--max N]
  python procmem.py scan <pid> utf16 <text> [--max N]
  python procmem.py dump <pid> <hexaddr> <len>

Used while validating the CODOL offline hand-off: scanning the game process for the
shared-memory names it opens (TCLS_TASMEMORY_<pid> / TCLS_SHELLMEMORY_<pid>) and for
marker bytes written into the mapping by the launcher proves the mapping was consumed.
"""

import ctypes
import ctypes.wintypes as wt
import sys

k32 = ctypes.WinDLL('kernel32', use_last_error=True)

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
MEM_COMMIT = 0x1000
PAGE_GUARD = 0x100

pass

class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [('BaseAddress', ctypes.c_void_p), ('AllocationBase', ctypes.c_void_p),
                ('AllocationProtect', wt.DWORD), ('RegionSize', ctypes.c_size_t),
                ('State', wt.DWORD), ('Protect', wt.DWORD), ('Type', wt.DWORD)]


k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p,
                               ctypes.POINTER(MEMORY_BASIC_INFORMATION), ctypes.c_size_t]
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]

TH32CS_SNAPMODULE = 0x8
TH32CS_SNAPMODULE32 = 0x10


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [('dwSize', wt.DWORD), ('th32ModuleID', wt.DWORD), ('th32ProcessID', wt.DWORD),
                ('GlblcntUsage', wt.DWORD), ('ProccntUsage', wt.DWORD),
                ('modBaseAddr', ctypes.c_void_p), ('modBaseSize', wt.DWORD),
                ('hModule', ctypes.c_void_p), ('szModule', wt.WCHAR * 256),
                ('szExePath', wt.WCHAR * 260)]


def _regions(h):
    addr = 0
    mbi = MEMORY_BASIC_INFORMATION()
    while k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
        base = mbi.BaseAddress or 0
        size = mbi.RegionSize
        if mbi.State == MEM_COMMIT and (mbi.Protect & 0xFF) in (0x02, 0x04, 0x20, 0x40, 0x80) \
                and not (mbi.Protect & PAGE_GUARD):
            yield base, size
        addr = base + size
        if addr <= base:
            break


def _read(h, base, size):
    buf = ctypes.create_string_buffer(size)
    got = ctypes.c_size_t()
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(base), buf, size, ctypes.byref(got)):
        return b''
    return buf.raw[:got.value]


def cmd_modules(pid):
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    me = MODULEENTRY32W()
    me.dwSize = ctypes.sizeof(me)
    ok = k32.Module32FirstW(snap, ctypes.byref(me))
    out = []
    while ok:
        out.append((me.modBaseAddr or 0, me.modBaseSize, me.szModule))
        ok = k32.Module32NextW(snap, ctypes.byref(me))
    k32.CloseHandle(snap)
    return out


def cmd_windows(pid):
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    res = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

    def cb(hwnd, lparam):
        wpid = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
        if wpid.value == pid:
            n = user32.GetWindowTextLengthW(hwnd)
            tbuf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, tbuf, n + 1)
            cbuf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, cbuf, 256)
            rect = wt.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            res.append((hwnd, cbuf.value, tbuf.value, bool(user32.IsWindowVisible(hwnd)),
                        (rect.left, rect.top, rect.right, rect.bottom)))
        return True

    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return res


def cmd_scan(pid, kind, text, maxhits=20):
    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        raise SystemExit('OpenProcess failed: %d (need admin?)' % ctypes.get_last_error())
    try:
        pat = text.encode('utf-16-le') if kind == 'utf16' else text.encode('ascii')
        hits = []
        for base, size in _regions(h):
            data = _read(h, base, min(size, 32 * 1024 * 1024))
            i = data.find(pat)
            while i >= 0 and len(hits) < maxhits:
                hits.append((base + i, base, size))
                i = data.find(pat, i + 1)
            if len(hits) >= maxhits:
                break
        return hits
    finally:
        k32.CloseHandle(h)


def cmd_scan_multi(pid, patterns, maxhits=3):
    """Single memory pass searching many patterns at once (much faster)."""
    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        raise SystemExit('OpenProcess failed: %d (need admin?)' % ctypes.get_last_error())
    try:
        pats = [(kind, text, (text.encode('utf-16-le') if kind == 'utf16'
                              else text.encode('ascii'))) for kind, text in patterns]
        res = {p[1]: [] for p in pats}
        for base, size in _regions(h):
            data = _read(h, base, min(size, 64 * 1024 * 1024))
            if not data:
                continue
            for kind, text, pat in pats:
                if len(res[text]) >= maxhits:
                    continue
                i = data.find(pat)
                while i >= 0 and len(res[text]) < maxhits:
                    res[text].append(base + i)
                    i = data.find(pat, i + 1)
        return res
    finally:
        k32.CloseHandle(h)


def cmd_dump(pid, addr, ln):
    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        raise SystemExit('OpenProcess failed: %d' % ctypes.get_last_error())
    try:
        data = _read(h, addr, ln)
    finally:
        k32.CloseHandle(h)
    for i in range(0, len(data), 16):
        chunk = data[i:i + 16]
        print('%08X  %-47s  %s' % (addr + i, ' '.join('%02X' % c for c in chunk),
                                   ''.join(chr(c) if 32 <= c < 127 else '.' for c in chunk)))


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    cmd = sys.argv[1]
    if cmd == 'modules':
        for b, s, n in cmd_modules(int(sys.argv[2])):
            print('%08X %9d  %s' % (b, s, n))
        return 0
    if cmd == 'windows':
        for hwnd, cls, title, vis, rect in cmd_windows(int(sys.argv[2])):
            print('hwnd=%s class=%-32s visible=%-5s title=%r rect=%s' %
                  (hwnd, cls, vis, title, rect))
        return 0
    if cmd == 'scan':
        pid, kind, text = int(sys.argv[2]), sys.argv[3], sys.argv[4]
        maxhits = 20
        if '--max' in sys.argv:
            maxhits = int(sys.argv[sys.argv.index('--max') + 1])
        hits = cmd_scan(pid, kind, text, maxhits)
        print('%d hit(s) for %s %r' % (len(hits), kind, text))
        for va, base, size in hits:
            print('  VA 0x%08X (region 0x%08X..0x%08X)' % (va, base, base + size))
        return 0
    if cmd == 'dump':
        cmd_dump(int(sys.argv[2]), int(sys.argv[3], 16), int(sys.argv[4], 0))
        return 0
    print(__doc__)
    return 1


if __name__ == '__main__':
    sys.exit(main())
