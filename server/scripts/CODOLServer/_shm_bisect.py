# -*- coding: utf-8 -*-
"""Bisect which byte range of the TAS payload makes the client crash.

Context: with the mapping TCLS_SHAREDMEMEMORY<pid> present,
  - all-zero payload  -> client survives
  - 'ready'+all-zero  -> client survives
  - full encrypted payload -> client dies in VMProtect with a bad pointer read

So some field inside the payload is treated as a pointer/offset. This script
sets one region at a time to a benign non-zero pattern and reports survival,
so we can find which offset the reader dereferences.

Regions probed (offsets into the 0x7AC block):
  hdr       0x000..0x010   header dwords
  block1    0x010..0x410   daemon data
  block2    0x410..0x490   second daemon block
  tail      0x490..0x7AC   fields + text
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

REGIONS = {
    'hdr': (0x000, 0x010),
    'block1': (0x010, 0x410),
    'block2': (0x410, 0x490),
    'tail': (0x490, 0x7AC),
}


def build(region, value):
    buf = bytearray(TAS_SIZE)
    struct.pack_into('<I', buf, 0x004, TAS_SIZE)
    if region == 'all':
        for i in range(0x000, TAS_SIZE, 4):
            struct.pack_into('<I', buf, i, value)
        struct.pack_into('<I', buf, 0x004, TAS_SIZE)
        return bytes(buf)
    lo, hi = REGIONS[region]
    for i in range(lo, hi, 4):
        struct.pack_into('<I', buf, i, value)
    struct.pack_into('<I', buf, 0x004, TAS_SIZE)
    return bytes(buf)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--region', choices=list(REGIONS) + ['all'], default=None)
    ap.add_argument('--start', type=lambda s: int(s, 0), default=None,
                    help='override region start (with --end)')
    ap.add_argument('--end', type=lambda s: int(s, 0), default=None,
                    help='override region end (with --start)')
    ap.add_argument('--payload-file', default=None,
                    help='use this raw 0x7AC payload file instead of synthesising one')
    ap.add_argument('--value', type=lambda s: int(s, 0), default=0x01010101)
    ap.add_argument('--ready', type=lambda s: int(s, 0), default=0)
    ap.add_argument('--root', default=os.path.join(PROJECT, 'COD OL'))
    ap.add_argument('--keep', type=float, default=14.0)
    ap.add_argument('--log', default=os.path.join(HERE, 'logs', 'bisect.jsonl'))
    args = ap.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(args.log)), exist_ok=True)
    root = os.path.abspath(args.root)
    exe = cl.find_game(root)
    cmdline = '"%s" -q' % exe

    si = cl.STARTUPINFOW()
    si.cb = ctypes.sizeof(si)
    pi = cl.PROCESS_INFORMATION()
    buf = ctypes.create_unicode_buffer(cmdline)
    ok = cl.k32.CreateProcessW(exe, buf, None, None, True, cl.CREATE_SUSPENDED,
                               None, root, ctypes.byref(si), ctypes.byref(pi))
    if not ok:
        raise SystemExit('CreateProcessW failed')
    pid = pi.dwProcessId

    session = script = None
    try:
        session = frida.attach(pid)
        script = session.create_script(open(PROBE_JS, encoding='utf-8').read())
        probe_log = args.log.replace('.jsonl', '.probe.jsonl')

        def _on_msg(m, d):
            payload = m.get('payload') if isinstance(m, dict) else None
            if isinstance(payload, dict):
                with open(probe_log, 'a', encoding='utf-8') as fh:
                    fh.write(json.dumps(payload, ensure_ascii=False, default=str) + '\n')

        script.on('message', _on_msg)
        script.load()
    except Exception:  # noqa: BLE001
        pass

    if args.payload_file:
        payload = bytearray(open(args.payload_file, 'rb').read())
        if len(payload) < TAS_SIZE:
            payload.extend(b'\x00' * (TAS_SIZE - len(payload)))
    elif args.region is None:
        raise SystemExit('--region is required unless --payload-file is given')
    elif args.start is not None and args.end is not None:
        payload = bytearray(TAS_SIZE)
        struct.pack_into('<I', payload, 0x004, TAS_SIZE)
        for i in range(args.start, args.end, 4):
            struct.pack_into('<I', payload, i, args.value)
    else:
        payload = bytearray(build(args.region, args.value))
    if not args.payload_file:
        struct.pack_into('<I', payload, 0x000, args.ready)
    handles = []
    try:
        handles.append(cl.create_mapping(cl.SHARED_NAME_FMT % pid, bytes(payload)))
    except OSError as exc:
        print('mapping failed: %s' % exc)

    cl.k32.ResumeThread(pi.hThread)

    deadline = time.time() + args.keep
    exitcode = None
    while time.time() < deadline:
        if cl.k32.WaitForSingleObject(pi.hProcess, 200) == 0:
            code = wt.DWORD()
            cl.k32.GetExitCodeProcess(pi.hProcess, ctypes.byref(code))
            exitcode = code.value
            break
    survived = exitcode is None
    rec = {'region': args.region, 'value': hex(args.value), 'ready': args.ready,
           'survived': survived, 'exitcode': exitcode}
    print(json.dumps(rec))
    with open(args.log, 'a', encoding='utf-8') as fh:
        fh.write(json.dumps(rec) + '\n')

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
    return 0 if survived else 1


if __name__ == '__main__':
    sys.exit(main())
