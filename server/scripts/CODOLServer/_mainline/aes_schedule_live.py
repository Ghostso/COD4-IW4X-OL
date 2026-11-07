#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aes_schedule_live.py -- keep the game alive and repeatedly scan its memory for
AES key schedules, while the harness primes the QoS channel.

The 8081 key is generated per call into a stack buffer, so the raw key is nearly
impossible to catch. The expanded schedule lives in the crypto object for much
longer, so we hunt for the 176/208/240-byte expansion and then verify it against
the captured 8081 ciphertexts.

Run elevated. Read-only.
"""

import argparse
import ctypes
import ctypes.wintypes as wt
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import suspend_host_redirect as S  # noqa: E402
import aes_schedule_hunt as AS     # noqa: E402

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

k32 = S.k32


def aes_ecb_dec(key, block):
    d = Cipher(algorithms.AES(key), modes.ECB()).decryptor()
    return d.update(block) + d.finalize()


def aes_ecb_enc(key, block):
    e = Cipher(algorithms.AES(key), modes.ECB()).encryptor()
    return e.update(block) + e.finalize()


def load_8081(path):
    out = []
    if not os.path.isfile(path):
        return out
    for line in open(path, encoding='utf-8', errors='replace'):
        try:
            o = json.loads(line)
        except ValueError:
            continue
        if o.get('port') != 8081 or not o.get('data_hex'):
            continue
        try:
            out.append(bytes.fromhex(o['data_hex']))
        except ValueError:
            pass
    return out


def scan_schedules(h, out_dir, log, deadline, ciphertexts):
    """Repeatedly scan for schedules; test any key against ciphertexts."""
    found = []
    tested = set()
    n_round = 0
    while time.time() < deadline:
        n_round += 1
        n_bytes = 0
        for base, size in S.regions(h):
            off = 0
            while off < size:
                want = min(0x100000, size - off)
                data = S.read_some(h, base + off, want)
                if data:
                    n_bytes += len(data)
                    cand = []
                    AS.scan_chunk(data, base + off, cand, lambda m: None)
                    for c in cand:
                        key = bytes.fromhex(c['key'])
                        if key in tested:
                            continue
                        tested.add(key)
                        ok16 = _test_key(key, ciphertexts)
                        log('SCHEDULE key=%s va=0x%08X match16=%d'
                            % (c['key'], c['va'], ok16))
                        if ok16:
                            found.append(c)
                off += want
        log('round %d scanned=%d bytes tested=%d schedules=%d'
            % (n_round, n_bytes, len(tested), len(found)))
        if found:
            break
        time.sleep(2.0)
    return found


def _test_key(key, ciphertexts):
    """How many 8081 blocks decrypt to something with a plausible header."""
    hits = 0
    for ct in ciphertexts[:9]:
        body = ct[:-4]
        if len(body) < 16:
            continue
        try:
            pt = aes_ecb_dec(key, body[:16])
        except Exception:
            continue
        if pt[:2] in (b'ur', b'us', b'ru', b'su'):
            hits += 1
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--packets', default='')
    ap.add_argument('--exe', required=True)
    ap.add_argument('--cwd', required=True)
    ap.add_argument('--seconds', type=float, default=150.0)
    ap.add_argument('--scan-seconds', type=float, default=120.0)
    ap.add_argument('--reply-variant', type=int, default=4)
    ap.add_argument('--advertise-port', type=int, default=8000)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    logf = open(os.path.join(args.out, 'schedule_live.log'), 'w',
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
    log('created suspended pid=%d' % pid)
    h = k32.OpenProcess(S.PROCESS_ALL_ACCESS, False, pid)
    log('handle=%s err=%d' % (h, ctypes.get_last_error()))
    if not h:
        k32.ResumeThread(pi.hThread)
        return 1

    stop = __import__('threading').Event()
    S.start_listeners(args.out, stop, args.reply_variant, '',
                      args.advertise_port)

    found_any = {}
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
                        found_any.setdefault(src.decode(), 0)
                        found_any[src.decode()] += 1
                        S.write_bytes(h, base + off + i, dst)
                        i += 1
            off += want
    log('redirects applied: %s' % found_any)

    k32.ResumeThread(pi.hThread)
    log('resumed')

    cap = args.packets or os.path.join(args.out, 'local_listeners.jsonl')
    cts = load_8081(cap)
    log('preloaded 8081 ciphertexts: %d' % len(cts))

    deadline = time.time() + args.scan_seconds
    res = scan_schedules(h, args.out, log, deadline, cts)
    if res:
        with open(os.path.join(args.out, 'aes_key_FOUND.json'), 'w',
                  encoding='utf-8') as fh:
            json.dump(res, fh, ensure_ascii=False, indent=2)
        log('KEY FOUND -> aes_key_FOUND.json')
    else:
        log('no schedule matched the ciphertext oracle')
    log('done pid=%d' % pid)
    logf.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
