#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
live_platform_key.py -- capture 8081 ciphertext and immediately scan the
unprotected platform processes for the AES key, within the SAME session.

Sequence:
  1. kill stale processes, launch the game via the verified harness
     (host redirect + TQoS replies) so the 8081 stage is reached
  2. wait for an 8081 datagram from that exact run
  3. enumerate TQMCenter / IIPSHostApp / CrossProxy and scan their memory for
     a key that decrypts that datagram
"""

import argparse
import ctypes
import ctypes.wintypes as wt
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import platform_key_scan as P  # noqa: E402

k32 = ctypes.WinDLL('kernel32', use_last_error=True)

ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
GAME = os.path.join(ROOT, 'run_codol_001', 'sandbox_ifs1_20260923',
                    'codoMP_client_shipRetail.exe')
CWD = os.path.join(ROOT, 'run_codol_001', 'sandbox_ifs1_20260923')


def kill_tree():
    for exe in ('codoMP_client_shipRetail.exe', 'TQMCenter.exe',
                'IIPSHostApp.exe', 'TP3Helper.exe', 'CrossProxy.exe'):
        subprocess.run(['taskkill', '/F', '/IM', exe, '/T'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)


def platform_pids():
    out = []
    for name in ('TQMCenter', 'IIPSHostApp', 'CrossProxy'):
        r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq %s.exe' % name,
                            '/FO', 'CSV', '/NH'],
                           capture_output=True, text=True)
        for line in r.stdout.splitlines():
            parts = [x.strip('"') for x in line.split('","')]
            if len(parts) >= 2 and parts[1].isdigit():
                out.append(int(parts[1]))
    return out


def wait_for_8081(path, timeout):
    t0 = time.time()
    while time.time() - t0 < timeout:
        pk = P.load_packets(path)
        if pk:
            return pk
        time.sleep(0.5)
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--seconds', type=float, default=240.0)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    logf = open(os.path.join(args.out, 'live_platform.log'), 'w',
                encoding='utf-8')

    def log(m):
        logf.write(m + '\n')
        logf.flush()
        print(m, flush=True)

    kill_tree()
    harness_out = os.path.join(args.out, 'harness')
    os.makedirs(harness_out, exist_ok=True)
    argv = [sys.executable, '-X', 'utf8', '-u',
            os.path.join(HERE, 'suspend_host_redirect.py'),
            '--exe', GAME, '--cwd', CWD, '--out', harness_out,
            '--seconds', str(args.seconds), '--reply-variant', '3']
    proc = subprocess.Popen(argv, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    log('harness pid=%d' % proc.pid)

    cap = os.path.join(harness_out, 'local_listeners.jsonl')
    packets = wait_for_8081(cap, 120.0)
    log('8081 packets=%d' % len(packets))
    if not packets:
        log('no 8081 traffic; aborting')
        proc.terminate()
        return 1

    pids = platform_pids()
    log('platform pids=%s' % pids)
    if not pids:
        proc.terminate()
        return 1

    found = []
    for pid in pids:
        h = k32.OpenProcess(0x0410, False, pid)
        if not h:
            log('pid=%d open failed err=%d' % (pid, ctypes.get_last_error()))
            continue
        t0 = time.time()
        tested = set()
        for base, size in P.regions(h):
            if time.time() - t0 > 150:
                break
            off = 0
            while off < size:
                want = min(0x100000, size - off)
                data = P.read_some(h, base + off, want)
                if data:
                    for m in P.PAT.finditer(data):
                        k = m.group()
                        if k in tested:
                            continue
                        tested.add(k)
                        hits, det = P.test_key(k, packets)
                        if hits >= 2:
                            rec = {'pid': pid, 'key': k.decode('ascii', 'replace'),
                                   'va': base + off + m.start(), 'hits': hits,
                                   'total': len(packets), 'details': det,
                                   'source': 'alnum'}
                            log('MATCH key=%s hits=%d/%d va=0x%08X'
                                % (rec['key'], hits, len(packets), rec['va']))
                            found.append(rec)
                    cand = []
                    P.AS.scan_chunk(data, base + off, cand, lambda m: None)
                    for c in cand:
                        k = bytes.fromhex(c['key'])
                        if k in tested:
                            continue
                        tested.add(k)
                        hits, det = P.test_key(k, packets)
                        if hits >= 2:
                            rec = {'pid': pid, 'key': c['key'], 'va': c['va'],
                                   'hits': hits, 'total': len(packets),
                                   'details': det, 'source': 'schedule'}
                            log('MATCH schedule key=%s hits=%d/%d va=0x%08X'
                                % (rec['key'], hits, len(packets), rec['va']))
                            found.append(rec)
                off += want
        log('pid=%d tested=%d matched=%d' % (pid, len(tested), len(found)))

    if found:
        best = max(found, key=lambda r: r['hits'])
        with open(os.path.join(args.out, 'aes_key_FOUND.json'), 'w',
                  encoding='utf-8') as fh:
            json.dump(best, fh, ensure_ascii=False, indent=2)
        log('KEY FOUND -> aes_key_FOUND.json')
    else:
        log('no key in platform processes for this session')
    proc.terminate()
    return 0


if __name__ == '__main__':
    sys.exit(main())
