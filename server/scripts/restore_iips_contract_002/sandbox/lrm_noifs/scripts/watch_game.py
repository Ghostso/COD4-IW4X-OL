#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
watch_game.py -- launch the game and sample its named kernel objects + windows over time.

  python watch_game.py [--mode baseline|full] [--no-shm] [--seconds 150] [--step 15]
                       [--out ../analysis_logs/game_watch.txt]

Writes a rolling report so a launcher run can be inspected after the fact (the game is
protected, so behavioural evidence -- which named objects it waits on -- matters).
"""

import argparse
import ctypes
import ctypes.wintypes as wt
import io
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prochandles as PH   # noqa: E402
import procmem as PM       # noqa: E402
import codol_launch as CL  # noqa: E402

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
INTERESTING = ('tcls', 'ten', 'tas', 'ace', 'protect', 'guard', 'shell', 'global\\',
               'cod', 'iips', 'ifs', 'tpg', 'qq', 'wegame', 'bugtrace')


def sample(pid, out):
    rows = []
    try:
        rows = PH.list_named(pid, ('Section', 'Event', 'Mutant', 'Semaphore'))
    except SystemExit as e:
        out.write('    handle scan failed: %s\n' % e)
    named = {}
    for t, hv, nm in rows:
        named[(t, nm)] = hv
    hits = [(t, nm) for (t, nm) in named if any(k in nm.lower() for k in INTERESTING)]
    out.write('    named objects total=%d, interesting=%d\n' % (len(named), len(hits)))
    for t, nm in sorted(hits):
        out.write('      %-9s %s\n' % (t, nm))
    try:
        wins = PM.cmd_windows(pid)
        out.write('    windows: %d\n' % len(wins))
        for hwnd, cls, title, vis, rect in wins:
            out.write('      hwnd=%s class=%s visible=%s title=%r rect=%s\n'
                      % (hwnd, cls, vis, title, rect))
    except Exception as e:  # noqa: BLE001
        out.write('    window enum failed: %s\n' % e)


def sample_net(pid, out):
    try:
        r = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, timeout=20)
        lines = [l for l in r.stdout.splitlines() if l.strip().endswith(str(pid))]
        out.write('    sockets: %d\n' % len(lines))
        for l in lines[:25]:
            out.write('      %s\n' % ' '.join(l.split()))
    except Exception as e:  # noqa: BLE001
        out.write('    netstat failed: %s\n' % e)


def marker_scan(pid, out):
    pats = (('ascii', 'CODOLBLOCK1-MARKER'), ('ascii', 'CODOL-TEXT-MARKER'),
            ('ascii', 'TCLS_TASMEMORY_'), ('utf16', 'TCLS_TASMEMORY_'),
            ('ascii', 'TCLS_SHELLMEMORY_'), ('utf16', 'TCLS_SHELLMEMORY_'))
    for kind, text in pats:
        try:
            hits = PM.cmd_scan(pid, kind, text, 5)
            out.write('    scan %-6s %-24s -> %d hit(s)\n' % (kind, text, len(hits)))
            for va, base, size in hits:
                out.write('        VA 0x%08X\n' % va)
        except SystemExit as e:
            out.write('    scan %s %s failed: %s\n' % (kind, text, e))
        out.flush()


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=('baseline', 'full'), default='baseline')
    ap.add_argument('--no-shm', action='store_true')
    ap.add_argument('--seconds', type=float, default=150)
    ap.add_argument('--step', type=float, default=15)
    ap.add_argument('--keep-alive', action='store_true',
                    help='keep the launcher process (and its mappings) alive for the run')
    ap.add_argument('--out', default=os.path.join(here, '..', '..', 'analysis_logs', 'game_watch.txt'))
    args = ap.parse_args()

    root = os.path.abspath(os.path.join(here, '..'))
    exe = CL.find_game(root)
    key = CL.filetime_key(exe)

    if args.mode == 'baseline':
        cmdline = '"%s" -q' % exe
    else:
        cmdline = '"%s" -q 0 -i 0 -s 0 -g 0 -u 0 -n  -m --1' % exe

    with io.open(args.out, 'w', encoding='utf-8', errors='replace') as out:
        out.write('cmdline: %s\ncwd: %s\nkey(ft): %s\n' % (cmdline, root, key.hex()))
        out.flush()

        si = CL.STARTUPINFOW()
        si.cb = ctypes.sizeof(si)
        pi = CL.PROCESS_INFORMATION()
        buf = ctypes.create_unicode_buffer(cmdline)
        ok = CL.k32.CreateProcessW(exe, buf, None, None, True, CL.CREATE_SUSPENDED,
                                   None, root, ctypes.byref(si), ctypes.byref(pi))
        if not ok:
            out.write('CreateProcessW failed: %d\n' % ctypes.get_last_error())
            return 1
        pid = pi.dwProcessId
        out.write('created pid=%d\n' % pid)

        handles = []
        if not args.no_shm:
            tas = CL.build_tas_payload(key, block1=b'CODOLBLOCK1-MARKER',
                                       text_utf8=b'CODOL-TEXT-MARKER')
            shell = CL.build_shell_payload()
            for nm, payload in ((CL.TAS_NAME_FMT % pid, tas), (CL.SHELL_NAME_FMT % pid, shell)):
                try:
                    handles.append(CL.create_mapping(nm, payload))
                    out.write('mapping %s (%d bytes) OK\n' % (nm, len(payload)))
                except OSError as e:
                    out.write('mapping %s FAILED: %s\n' % (nm, e))
        out.flush()
        CL.k32.ResumeThread(pi.hThread)
        out.write('resumed\n')
        out.flush()

        t0 = time.time()
        while time.time() - t0 < args.seconds:
            time.sleep(args.step)
            el = time.time() - t0
            code = wt.DWORD()
            alive = CL.k32.WaitForSingleObject(pi.hProcess, 0) != 0
            if alive:
                out.write('\n[t+%.0fs] alive\n' % el)
                sample(pid, out)
                sample_net(pid, out)
                if el <= 30:
                    marker_scan(pid, out)
            else:
                CL.k32.GetExitCodeProcess(pi.hProcess, ctypes.byref(code))
                out.write('\n[t+%.0fs] EXITED code=0x%08X (%d)\n' % (el, code.value, code.value))
                break
            out.flush()
        for h in handles:
            CL.k32.CloseHandle(h)
    return 0


if __name__ == '__main__':
    sys.exit(main())
