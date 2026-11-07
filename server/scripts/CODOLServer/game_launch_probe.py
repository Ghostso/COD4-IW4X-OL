#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Launch codoMP_client_shipRetail.exe suspended, inject the network/hand-off
probe, create the TAS/SHELL mappings, then resume and capture everything.

This is the "see the lobby protocol" step: we cannot write a lobby server until
we know what the game sends and where it sends it. The probe logs connect()
targets, initial payload bytes, and whether the game opens the TCLS TAS/SHELL
shared-memory objects.

Reuses the hand-off implementation in COD OL/scripts/codol_launch.py.
"""

import argparse
import ctypes
import ctypes.wintypes as wt
import json
import os
import sys
import time

import frida

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
SCRIPTS = os.path.join(PROJECT, 'COD OL', 'scripts')
sys.path.insert(0, SCRIPTS)

import codol_launch as cl  # noqa: E402

PROBE_JS = os.path.join(HERE, 'game_net_probe.js')


def log(rec, path):
    line = json.dumps(rec, ensure_ascii=False, default=str)
    print(line, flush=True)
    if path:
        with open(path, 'a', encoding='utf-8') as fh:
            fh.write(line + '\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=('baseline', 'full'), default='baseline')
    ap.add_argument('--root', default=os.path.join(PROJECT, 'COD OL'))
    ap.add_argument('-q', '--uid', default='0')
    ap.add_argument('-i', dest='d1', default='0')
    ap.add_argument('-s', dest='d2', default='0')
    ap.add_argument('-g', dest='d3', default='0')
    ap.add_argument('-u', dest='u2', default='0')
    ap.add_argument('-n', dest='name', default='')
    ap.add_argument('--extra', default='-m --1')
    ap.add_argument('--keep', type=float, default=30.0)
    ap.add_argument('--no-shm', action='store_true')
    ap.add_argument('--safe-shm', action='store_true',
                    help='use the zeroed safe TAS payload instead of the encrypted one')
    ap.add_argument('--ready', type=lambda s: int(s, 0), default=0,
                    help='ready flag for --safe-shm (0 or 1)')
    ap.add_argument('--no-frida', action='store_true')
    ap.add_argument('--script', default=PROBE_JS,
                    help='Frida script to inject before resuming the game')
    ap.add_argument('--log', default=os.path.join(HERE, 'logs', 'game_probe.jsonl'))
    args = ap.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(args.log)), exist_ok=True)
    root = os.path.abspath(args.root)
    exe = cl.find_game(root)
    key = cl.filetime_key(exe)
    print('[i] exe : %s' % exe, flush=True)
    print('[i] key : %s' % key.hex(), flush=True)

    if args.mode == 'baseline':
        cmdline = '"%s" -q' % exe
    else:
        cmdline = '"%s" -q %s -i %s -s %s -g %s -u %s -n %s' % (
            exe, args.uid, args.d1, args.d2, args.d3, args.u2, args.name)
        if args.extra:
            cmdline += ' ' + args.extra
    print('[i] cmd : %s' % cmdline, flush=True)

    si = cl.STARTUPINFOW()
    si.cb = ctypes.sizeof(si)
    pi = cl.PROCESS_INFORMATION()
    buf = ctypes.create_unicode_buffer(cmdline)
    ok = cl.k32.CreateProcessW(exe, buf, None, None, True, cl.CREATE_SUSPENDED,
                               None, root, ctypes.byref(si), ctypes.byref(pi))
    if not ok:
        raise SystemExit('CreateProcessW failed: %d' % ctypes.get_last_error())
    pid = pi.dwProcessId
    log({'kind': 'created_suspended', 'pid': pid, 'cmdline': cmdline}, args.log)

    session = None
    script = None
    if not args.no_frida:
        try:
            session = frida.attach(pid)
            with open(args.script, 'r', encoding='utf-8') as fh:
                source = fh.read()
            script = session.create_script(source)
            script.on('message', lambda m, d: log(
                dict(m.get('payload'), label='probe') if isinstance(m.get('payload'), dict)
                else {'kind': 'raw', 'raw': m}, args.log))
            script.load()
            log({'kind': 'frida_attached', 'pid': pid}, args.log)
        except Exception as exc:  # noqa: BLE001
            log({'kind': 'frida_attach_failed', 'pid': pid, 'error': repr(exc)}, args.log)

    handles = []
    if not args.no_shm:
        if args.safe_shm:
            tas_payload = cl.build_safe_shared_payload(ready=args.ready)
        else:
            tas_payload = cl.build_tas_payload(key, text_utf8=args.name.encode('utf-8'))
        shell_payload = cl.build_shell_payload()
        if args.safe_shm:
            # Only the reader-side name; TAS_/SHELL_ make the client take a
            # different, crashing path.
            names = [(cl.SHARED_NAME_FMT % pid, tas_payload)]
        else:
            names = [(cl.SHARED_NAME_FMT % pid, tas_payload),
                     (cl.TAS_NAME_FMT % pid, tas_payload),
                     (cl.SHELL_NAME_FMT % pid, shell_payload)]
        for name, payload in names:
            try:
                handles.append(cl.create_mapping(name, payload))
                log({'kind': 'mapping_created', 'pid': pid, 'name': name,
                     'size': len(payload)}, args.log)
            except OSError as exc:
                log({'kind': 'mapping_failed', 'pid': pid, 'name': name,
                     'error': str(exc)}, args.log)

    cl.k32.ResumeThread(pi.hThread)
    log({'kind': 'resumed', 'pid': pid}, args.log)

    deadline = time.time() + args.keep
    exitcode = None
    while time.time() < deadline:
        if cl.k32.WaitForSingleObject(pi.hProcess, 250) == 0:
            code = wt.DWORD()
            cl.k32.GetExitCodeProcess(pi.hProcess, ctypes.byref(code))
            exitcode = code.value
            break
    log({'kind': 'finished', 'pid': pid, 'exitcode': exitcode,
         'still_running': exitcode is None}, args.log)

    if script:
        try:
            script.unload()
        except Exception:  # noqa: BLE001
            pass
    if session:
        try:
            session.detach()
        except Exception:  # noqa: BLE001
            pass
    for h in handles:
        try:
            cl.k32.CloseHandle(h)
        except Exception:  # noqa: BLE001
            pass
    try:
        cl.k32.CloseHandle(pi.hThread)
    except Exception:  # noqa: BLE001
        pass
    try:
        cl.k32.CloseHandle(pi.hProcess)
    except Exception:  # noqa: BLE001
        pass
    return 0


if __name__ == '__main__':
    sys.exit(main())
