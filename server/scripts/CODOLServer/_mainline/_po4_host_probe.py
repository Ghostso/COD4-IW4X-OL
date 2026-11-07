# -*- coding: utf-8 -*-
"""
_po4_host_probe.py - probe the IIPS host chain (popup-origin line, task PO4).

Read-only w.r.t. the game.  It does three things:
  1. snapshots the current named-pipe namespace
  2. launches IIPSHostApp.exe <mode> iipslaunch from a given IIPS directory
  3. re-snapshots pipes and IIPS\\HostPid, then kills the host again

Nothing is patched, no system network setting is touched.

Usage:
    python -X utf8 _po4_host_probe.py --dir "COD OL\\IIPS"
    python -X utf8 _po4_host_probe.py --dir "run_codol_001\\sandbox_ifs1_20260923\\IIPS"
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import json
import os
import subprocess
import sys
import time

ROOT = r'D:\BaiduNetdiskDownload\使命召唤OL'

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
ntdll = ctypes.WinDLL('ntdll', use_last_error=True)


class UNICODE_STRING(ctypes.Structure):
    _fields_ = [('Length', wt.USHORT),
                ('MaximumLength', wt.USHORT),
                ('Buffer', ctypes.c_void_p)]


def enum_pipes():
    """Return the raw NT pipe-name list."""
    ret_len = wt.ULONG(0)
    ntdll.NtQueryDirectoryFile.restype = ctypes.c_long
    # Use the simpler Win32 route: '\\.\pipe\' directory listing.
    names = []
    k32.FindFirstFileW.restype = wt.HANDLE
    k32.FindFirstFileW.argtypes = [wt.LPCWSTR, ctypes.c_void_p]
    k32.FindNextFileW.argtypes = [wt.HANDLE, ctypes.c_void_p]

    class WIN32_FIND_DATAW(ctypes.Structure):
        _fields_ = [('dwFileAttributes', wt.DWORD),
                    ('ftCreationTime', wt.FILETIME),
                    ('ftLastAccessTime', wt.FILETIME),
                    ('ftLastWriteTime', wt.FILETIME),
                    ('nFileSizeHigh', wt.DWORD),
                    ('nFileSizeLow', wt.DWORD),
                    ('dwReserved0', wt.DWORD),
                    ('dwReserved1', wt.DWORD),
                    ('cFileName', wt.WCHAR * 260),
                    ('cAlternateFileName', wt.WCHAR * 14)]

    fd = WIN32_FIND_DATAW()
    h = k32.FindFirstFileW('\\\\.\\pipe\\*', ctypes.byref(fd))
    INVALID = ctypes.c_void_p(-1).value
    if h in (INVALID, None):
        return names
    names.append(fd.cFileName)
    hh = wt.HANDLE(h)
    while k32.FindNextFileW(hh, ctypes.byref(fd)):
        names.append(fd.cFileName)
    k32.FindClose(hh)
    return names


def read_hostpid(iips_dir):
    p = os.path.join(iips_dir, 'HostPid')
    if not os.path.exists(p):
        return ('missing', os.path.getsize(p) if os.path.exists(p) else None)
    raw = open(p, 'rb').read()
    if len(raw) == 0:
        return ('empty', 0)
    for enc in ('utf-16-le', 'ascii'):
        try:
            return (raw.decode(enc).strip('\x00\r\n '), len(raw))
        except Exception:
            pass
    return (raw.hex(), len(raw))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default=os.path.join(ROOT, 'COD OL', 'IIPS'))
    ap.add_argument('--mode-args', default='/mode iipslaunch')
    ap.add_argument('--seconds', type=float, default=12.0)
    ap.add_argument('--no-launch', action='store_true')
    ap.add_argument('--out', default='')
    args = ap.parse_args()

    iips_dir = args.dir if os.path.isabs(args.dir) else os.path.join(ROOT, args.dir)
    exe = os.path.join(iips_dir, 'IIPSHostApp.exe')
    report = {'iips_dir': iips_dir, 'exe_exists': os.path.isfile(exe)}

    before = enum_pipes()
    report['pipes_before_count'] = len(before)
    report['pipes_before_match'] = sorted(
        [n for n in before if any(k in n.lower() for k in ('iips', 'tenio', 'tpf', 'md5'))])
    report['hostpid_before'] = read_hostpid(iips_dir)

    if not args.no_launch and os.path.isfile(exe):
        cmd = [exe] + args.mode_args.split()
        report['launch_cmd'] = cmd
        proc = subprocess.Popen(cmd, cwd=iips_dir)
        report['launched_pid'] = proc.pid
        samples = []
        t0 = time.time()
        while time.time() - t0 < args.seconds:
            time.sleep(1.0)
            hp = read_hostpid(iips_dir)
            samples.append({'t': round(time.time() - t0, 2), 'hostpid': hp,
                            'alive': proc.poll() is None})
        report['samples'] = samples
        after = enum_pipes()
        report['pipes_after_count'] = len(after)
        report['pipes_after_new'] = sorted(set(after) - set(before))
        report['pipes_after_match'] = sorted(
            [n for n in after if any(k in n.lower() for k in ('iips', 'tenio', 'tpf'))])
        report['hostpid_after'] = read_hostpid(iips_dir)
        try:
            proc.terminate()
        except Exception:
            pass
    else:
        report['launch_cmd'] = None

    txt = json.dumps(report, indent=2, ensure_ascii=False)
    print(txt)
    if args.out:
        out = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, 'w', encoding='utf-8').write(txt)
        print('\nwrote', out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
