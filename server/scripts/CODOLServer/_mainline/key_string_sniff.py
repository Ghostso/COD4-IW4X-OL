#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
key_string_sniff.py -- recover the per-session 8081 AES key from the live
process by its distinctive alphabet.

ProtocalHandler.dll generates a 16-byte key from:
    ABCDEFGHIJKMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789
(note: no L, O, 0 or 1) and SetKey copies those 16 bytes into the crypto
object at object+0x50 before expanding. So the raw key persists in memory as
a 16-character string over that exact alphabet.

This tool scans memory for such strings, captures a real 8081 datagram from the
same process, and tests candidates with AES-ECB.

Run elevated. Read-only.
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

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

k32 = S.k32

ALPHABET = 'ABCDEFGHIJKMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789'
PAT = re.compile(('[' + ALPHABET + ']{16}').encode())


def aes_ecb_dec(key, block):
    d = Cipher(algorithms.AES(key), modes.ECB()).decryptor()
    return d.update(block) + d.finalize()


def score_key(key, packets):
    """Return how many 8081 packets look like a plausible decryption."""
    hits = 0
    details = []
    for i, pkt in enumerate(packets[:9]):
        body = pkt[:-4]
        if len(body) < 16:
            continue
        try:
            pt = aes_ecb_dec(key, body[:16])
        except Exception:
            continue
        if pt[:2] in (b'ur', b'us', b'ru', b'su'):
            hits += 1
            details.append({'pkt': i, 'pt': pt.hex()})
    return hits, details


def load_packets(path):
    out = []
    if not os.path.isfile(path):
        return out
    for line in open(path, encoding='utf-8', errors='replace'):
        try:
            o = json.loads(line)
        except ValueError:
            continue
        if o.get('port') == 8081 and o.get('data_hex'):
            try:
                out.append(bytes.fromhex(o['data_hex']))
            except ValueError:
                pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--exe', required=True)
    ap.add_argument('--cwd', required=True)
    ap.add_argument('--seconds', type=float, default=150.0)
    ap.add_argument('--reply-variant', type=int, default=4)
    ap.add_argument('--advertise-port', type=int, default=8000)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    logf = open(os.path.join(args.out, 'key_sniff.log'), 'w',
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

    stop = threading.Event()
    S.start_listeners(args.out, stop, args.reply_variant, '',
                      args.advertise_port)
    # initial host redirects
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

    cap = os.path.join(args.out, 'local_listeners.jsonl')
    t0 = time.time()
    candidates = {}
    packets = []
    next_scan = 0.0
    next_patch = 0.0
    late = {}
    found = None

    while time.time() - t0 < args.seconds:
        el = time.time() - t0
        if el <= 60.0 and el >= next_patch:
            next_patch = el + 0.5
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
                                va = base + off + i
                                if va not in late.setdefault(src.decode(), set()):
                                    late[src.decode()].add(va)
                                    S.write_bytes(h, va, dst)
                                    log('late-patch %s@0x%08X'
                                        % (src.decode(), va))
                                i += 1
                    off += want
        # late host patches
        for base, size in S.regions(h):
            off = 0
            while off < size:
                want = min(0x100000, size - off)
                data = S.read_some(h, base + off, want)
                if data:
                    for m in PAT.finditer(data):
                        s = m.group().decode('ascii', 'replace')
                        candidates.setdefault(s, base + off + m.start())
                off += want
        new_packets = load_packets(cap)
        if new_packets:
            packets = new_packets
        if packets and candidates:
            log('have %d packets / %d candidates' % (len(packets),
                                                     len(candidates)))
            for key_s, va in list(candidates.items()):
                hits, det = score_key(key_s.encode(), packets)
                if hits:
                    found = {'key': key_s, 'va': va, 'hits': hits,
                             'details': det}
                    log('*** KEY CANDIDATE %s va=0x%08X hits=%d'
                        % (key_s, va, hits))
                    if hits == len(packets):
                        break
            if found and found['hits'] == len(packets):
                break
        if time.time() - t0 > next_scan:
            next_scan = time.time() - t0 + 15
            log('t=%.0fs packets=%d alnum16_candidates=%d'
                % (time.time() - t0, len(packets), len(candidates)))
        time.sleep(0.5)

    if found:
        with open(os.path.join(args.out, 'aes_key_FOUND.json'), 'w',
                  encoding='utf-8') as fh:
            json.dump(found, fh, ensure_ascii=False, indent=2)
        log('KEY FOUND -> aes_key_FOUND.json')
    else:
        log('no matching key string found')
    stop.set()
    log('done pid=%d' % pid)
    logf.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
