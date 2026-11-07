#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Isolate which part of the TCLS hand-off block crashes the client.

The client aborts with 0xC0000005 as soon as we create TCLS_SHAREDMEMEMORY<pid>.
This script tries progressively more faithful payloads so we can find the field
the reader dereferences.

Variants:
  zero      1964 zero bytes                     (is the object itself enough?)
  ready     0x7AC header only, ready=1          (does it read the size field?)
  noready   0x7AC header, ready=0
  full      the codol_launch TAS payload (encrypted)
"""

import argparse
import ctypes
import ctypes.wintypes as wt
import json
import os
import struct
import sys
import time

import frida

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PROJECT, 'COD OL', 'scripts'))

import codol_launch as cl  # noqa: E402

PROBE_JS = os.environ.get('CODOL_PROBE_JS') or os.path.join(HERE, 'game_net_probe.js')
TAS_SIZE = 0x7AC


def log(rec, path):
    line = json.dumps(rec, ensure_ascii=False, default=str)
    print(line, flush=True)
    if path:
        with open(path, 'a', encoding='utf-8') as fh:
            fh.write(line + '\n')


def payload_for(variant, key, name):
    if variant == 'zero':
        return b'\x00' * TAS_SIZE
    if variant == 'ready':
        buf = bytearray(TAS_SIZE)
        struct.pack_into('<I', buf, 0x000, 1)
        struct.pack_into('<I', buf, 0x004, TAS_SIZE)
        return bytes(buf)
    if variant == 'noready':
        buf = bytearray(TAS_SIZE)
        struct.pack_into('<I', buf, 0x000, 0)
        struct.pack_into('<I', buf, 0x004, TAS_SIZE)
        return bytes(buf)
    if variant == 'full':
        return cl.build_tas_payload(key, text_utf8=name.encode('utf-8'))
    raise ValueError(variant)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--variant', required=True,
                    choices=('zero', 'ready', 'noready', 'full'))
    ap.add_argument('--root', default=os.path.join(PROJECT, 'COD OL'))
    ap.add_argument('--keep', type=float, default=20.0)
    ap.add_argument('--only-shared', action='store_true',
                    help='create only TCLS_SHAREDMEMEMORY<pid>')
    ap.add_argument('--log', default=os.path.join(HERE, 'logs', 'shm_variant.jsonl'))
    args = ap.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(args.log)), exist_ok=True)
    root = os.path.abspath(args.root)
    exe = cl.find_game(root)
    key = cl.filetime_key(exe)
    cmdline = '"%s" -q' % exe

    si = cl.STARTUPINFOW()
    si.cb = ctypes.sizeof(si)
    pi = cl.PROCESS_INFORMATION()
    buf = ctypes.create_unicode_buffer(cmdline)
    ok = cl.k32.CreateProcessW(exe, buf, None, None, True, cl.CREATE_SUSPENDED,
                               None, root, ctypes.byref(si), ctypes.byref(pi))
    if not ok:
        raise SystemExit('CreateProcessW failed: %d' % ctypes.get_last_error())
    pid = pi.dwProcessId
    log({'kind': 'created', 'pid': pid, 'variant': args.variant}, args.log)

    session = None
    script = None
    try:
        session = frida.attach(pid)
        with open(PROBE_JS, 'r', encoding='utf-8') as fh:
            source = fh.read()
        script = session.create_script(source)
        script.on('message', lambda m, d: log(
            dict(m.get('payload'), label='probe') if isinstance(m.get('payload'), dict)
            else {'kind': 'raw', 'raw': m}, args.log))
        script.load()
    except Exception as exc:  # noqa: BLE001
        log({'kind': 'frida_failed', 'error': repr(exc)}, args.log)

    payload = payload_for(args.variant, key, '')
    handles = []
    names = [(cl.SHARED_NAME_FMT % pid, payload)]
    if not args.only_shared:
        names.append((cl.TAS_NAME_FMT % pid, payload))
        names.append((cl.SHELL_NAME_FMT % pid, cl.build_shell_payload()))
    for name, data in names:
        try:
            handles.append(cl.create_mapping(name, data))
            log({'kind': 'mapping_created', 'pid': pid, 'name': name, 'size': len(data)}, args.log)
        except OSError as exc:
            log({'kind': 'mapping_failed', 'name': name, 'error': str(exc)}, args.log)

    cl.k32.ResumeThread(pi.hThread)
    log({'kind': 'resumed', 'pid': pid}, args.log)

    deadline = time.time() + args.keep
    exitcode = None
    while time.time() < deadline:
        if cl.k32.WaitForSingleObject(pi.hProcess, 200) == 0:
            code = wt.DWORD()
            cl.k32.GetExitCodeProcess(pi.hProcess, ctypes.byref(code))
            exitcode = code.value
            break
    log({'kind': 'finished', 'pid': pid, 'variant': args.variant,
         'exitcode': exitcode, 'still_running': exitcode is None}, args.log)

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
    for h in (pi.hThread, pi.hProcess):
        try:
            cl.k32.CloseHandle(h)
        except Exception:  # noqa: BLE001
            pass
    return 0


if __name__ == '__main__':
    sys.exit(main())

