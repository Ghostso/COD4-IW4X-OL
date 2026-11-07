#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Watch what the running CODOL client tries to connect to, from outside.

Polls netstat for the game + platform PIDs so we see the real connection
attempts (including failures), which is what actually drives the [100] state.
"""

import argparse
import ctypes
import ctypes.wintypes as wt
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import suspend_host_redirect as S  # noqa: E402

k32 = S.k32


def kill_tree():
    for exe in ('codoMP_client_shipRetail.exe', 'TQMCenter.exe',
                'IIPSHostApp.exe', 'TP3Helper.exe', 'CrossProxy.exe'):
        subprocess.run(['taskkill', '/F', '/IM', exe, '/T'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)


def netstat_by_pid(pids):
    try:
        out = subprocess.run(['netstat', '-ano'], capture_output=True,
                             timeout=15).stdout
    except Exception:
        return {}
    if out is None:
        return {}
    out = out.decode('gbk', 'replace')
    res = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        pid_s = parts[-1]
        if not pid_s.isdigit() or int(pid_s) not in pids:
            continue
        res.setdefault(int(pid_s), []).append(' '.join(parts[:-1]))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--exe', required=True)
    ap.add_argument('--cwd', required=True)
    ap.add_argument('--seconds', type=float, default=120.0)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    logf = open(os.path.join(args.out, 'watch.log'), 'w', encoding='utf-8')

    def log(m):
        logf.write(m + '\n')
        logf.flush()
        print(m, flush=True)

    ok, err = S.enable_debug()
    log('SeDebugPrivilege=%s err=%d' % (ok, err))
    kill_tree()

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
    log('pid=%d (clean run: NO host redirection)' % pid)

    # Clean run: no hostname rewriting, so we observe the real destinations.
    k32.ResumeThread(pi.hThread)

    seen = {}
    t0 = time.time()
    while time.time() - t0 < args.seconds:
        r = subprocess.run(['tasklist', '/FO', 'CSV', '/NH'],
                           capture_output=True)
        tsv = (r.stdout or b'').decode('gbk', 'replace')
        pids = {pid}
        for line in tsv.splitlines():
            parts = [x.strip('"') for x in line.split('","')]
            if len(parts) >= 2 and parts[0].lower() in (
                    'tqmcenter.exe', 'iipshostapp.exe', 'crossproxy.exe',
                    'tp3helper.exe'):
                pids.add(int(parts[1]))
        ns = netstat_by_pid(pids)
        for p, items in ns.items():
            for it in items:
                if it not in seen.get(p, set()):
                    seen.setdefault(p, set()).add(it)
                    log('pid=%d %s' % (p, it))
        time.sleep(1.0)

    with open(os.path.join(args.out, 'connects.json'), 'w',
              encoding='utf-8') as fh:
        json.dump({str(k): sorted(v) for k, v in seen.items()}, fh, indent=2)
    log('done pid=%d' % pid)
    logf.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
