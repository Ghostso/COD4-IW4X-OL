#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe the live game process for lobby/GDP state right after [100] appears.

Uses the pre-arm ALL_ACCESS handle so ACE does not block the reads. Looks for
the GDP protocol strings and any endpoint-like ASCII in the process, which
reveals what the client tried to use for the lobby.
"""

import argparse
import ctypes
import json
import os
import re
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import suspend_host_redirect as S  # noqa: E402

k32 = S.k32

GDP_TERMS = [b'GDP_CF_', b'GDPPkg', b'LobbyName', b'lobby', b'ENterserver',
             b'GAMESERVERPORTINFO', b'SCROLLSERVERLIST', b'auth/', b'/auth',
             b'queue/', b'member/', b'tencent_ticket', b'title_id']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--exe', required=True)
    ap.add_argument('--cwd', required=True)
    ap.add_argument('--seconds', type=float, default=90.0)
    ap.add_argument('--reply-variant', type=int, default=3)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    logf = open(os.path.join(args.out, 'lobby_state.log'), 'w',
                encoding='utf-8')

    def log(m):
        logf.write(m + '\n')
        logf.flush()
        print(m, flush=True)

    ok, err = S.enable_debug()
    log('SeDebugPrivilege=%s err=%d' % (ok, err))

    si = S.STARTUPINFOW()
    si.cb = ctypes.sizeof(si)
    pi = S.PROCESS_INFORMATION()
    cmd = '"%s" -q --disable-gpu --disable-gpu-compositing' % args.exe
    buf = ctypes.create_unicode_buffer(cmd)
    if not k32.CreateProcessW(args.exe, buf, None, None, True,
                              S.CREATE_SUSPENDED, None, args.cwd,
                              ctypes.byref(si), ctypes.byref(pi)):
        raise SystemExit('CreateProcess failed: %d' % ctypes.get_last_error())
    pid = pi.dwProcessId
    log('pid=%d' % pid)
    h = k32.OpenProcess(S.PROCESS_ALL_ACCESS, False, pid)
    log('handle=%s' % h)
    if not h:
        k32.ResumeThread(pi.hThread)
        return 1

    stop = threading.Event()
    S.start_listeners(args.out, stop, args.reply_variant, '', 8000)
    S.create_tcls_handoff(pid, log)
    # host redirection
    for base, size in S.regions(h):
        off = 0
        while off < size:
            want = min(0x100000, size - off)
            data = S.read_some(h, base + off, want)
            if data:
                for src, dst in S.REDIRECTS.items():
                    i = 0
                    while True:
                        i = data.find(src, i)
                        if i < 0:
                            break
                        S.write_bytes(h, base + off + i, dst)
                        i += 1
            off += want
    k32.ResumeThread(pi.hThread)
    log('resumed')

    # wait for the client to reach the [100] state
    time.sleep(30)

    hits = {}
    seen = {}
    for base, size in S.regions(h):
        off = 0
        while off < size:
            want = min(0x100000, size - off)
            data = S.read_some(h, base + off, want)
            if data:
                for t in GDP_TERMS:
                    start = 0
                    while True:
                        i = data.find(t, start)
                        if i < 0:
                            break
                        va = base + off + i
                        lo = max(0, i - 80)
                        hi = min(len(data), i + 160)
                        ctx = data[lo:hi]
                        txt = ''.join(chr(c) if 32 <= c < 127 else '.'
                                      for c in ctx)
                        key = (t.decode(), txt)
                        if key not in seen:
                            seen[key] = va
                            hits.setdefault(t.decode(), []).append(
                                {'va': va, 'ctx': txt})
                        start = i + 1
            off += want
        if len(seen) > 2000:
            break

    with open(os.path.join(args.out, 'lobby_state.json'), 'w',
              encoding='utf-8') as fh:
        json.dump(hits, fh, ensure_ascii=False, indent=2)
    for t, rows in hits.items():
        log('== %s : %d unique' % (t, len(rows)))
        for r in rows[:6]:
            log('   %08X %s' % (r['va'], r['ctx'][:150]))
    log('done pid=%d' % pid)
    logf.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
