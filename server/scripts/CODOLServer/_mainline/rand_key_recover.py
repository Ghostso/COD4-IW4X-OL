#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rand_key_recover.py -- recover the 8081 AES key without catching the stack
value, by replaying the MSVCRT rand() sequence.

ProtocalHandler.dll builds the 16-byte key with:
    idx = -(_ftol(rand() * -56.0 * (1/32768)))
    key[i] = "ABCDEFGHIJKMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789"[idx]

MSVCRT rand() is the classic LCG:
    state = state*214013 + 2531011
    out   = (state >> 16) & 0x7fff

We locate the `holdrand` global from the rand() machine code, sample it, and
test candidate keys (all small offsets around the sampled state) against a real
8081 datagram captured from the same process.

Run elevated. Read-only.
"""

import argparse
import ctypes
import json
import os
import struct
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import suspend_host_redirect as S  # noqa: E402

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

k32 = S.k32

ALPHABET = b'ABCDEFGHIJKMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789'
LCG_A = 214013
LCG_C = 2531011
MASK32 = 0xFFFFFFFF


def aes_ecb_dec(key, block):
    d = Cipher(algorithms.AES(key), modes.ECB()).decryptor()
    return d.update(block) + d.finalize()


def key_from_rand_outputs(outputs):
    out = bytearray()
    for r in outputs:
        # C truncation toward zero of a negative float
        eax = int(r * -56.0 * (1.0 / 32768.0))
        idx = -eax
        if idx < 0:
            idx = 0
        if idx >= len(ALPHABET):
            idx = len(ALPHABET) - 1
        out.append(ALPHABET[idx])
    return bytes(out)


def next_state(s):
    return (s * LCG_A + LCG_C) & MASK32


def prev_state(s):
    # modular inverse of 214013 mod 2^32
    return ((s - LCG_C) * 3115528533) & MASK32


def outputs_from(state, n=16):
    out = []
    for _ in range(n):
        state = next_state(state)
        out.append((state >> 16) & 0x7FFF)
    return out


def score_key(key, packets):
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


def find_holdrand(h, log):
    """Find the MSVCRT rand() code and return the holdrand VA."""
    pat = b'\x69\x05'  # imul eax, dword ptr [imm32], imm32
    for base, size in S.regions(h):
        off = 0
        while off < size:
            want = min(0x100000, size - off)
            data = S.read_some(h, base + off, want)
            if data:
                i = 0
                while True:
                    i = data.find(pat, i)
                    if i < 0:
                        break
                    if i + 10 <= len(data):
                        addr = struct.unpack_from('<I', data, i + 2)[0]
                        imm = struct.unpack_from('<I', data, i + 6)[0]
                        if imm == 0x343FD:
                            log('rand() candidate at 0x%08X holdrand=0x%08X'
                                % (base + off + i, addr))
                            return addr
                    i += 1
            off += want
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--exe', required=True)
    ap.add_argument('--cwd', required=True)
    ap.add_argument('--seconds', type=float, default=150.0)
    ap.add_argument('--reply-variant', type=int, default=3)
    ap.add_argument('--advertise-port', type=int, default=8000)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    logf = open(os.path.join(args.out, 'rand_recover.log'), 'w',
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

    holdrand = None
    t0 = time.time()
    while time.time() - t0 < 20 and holdrand is None:
        holdrand = find_holdrand(h, log)
        time.sleep(0.5)
    if not holdrand:
        log('could not locate holdrand')
        return 1

    cap = os.path.join(args.out, 'local_listeners.jsonl')
    seen_states = []
    found = None
    t0 = time.time()
    next_patch = 0.0
    late = {}
    while time.time() - t0 < args.seconds:
        # Late-patch hostnames in modules that load after resume (notably
        # tqos.gamesafe.qq.com, whose absence suppresses the 8081 stage).
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
        st = S.read_some(h, holdrand, 4)
        if len(st) == 4:
            s = struct.unpack('<I', st)[0]
            if not seen_states or seen_states[-1] != s:
                seen_states.append(s)
                if len(seen_states) > 20000:
                    seen_states = seen_states[-20000:]
        packets = load_packets(cap)
        if packets and seen_states:
            for si_value in seen_states[-300:]:
                # Test offsets around the observed state in both directions.
                states = [si_value]
                cur = si_value
                for _ in range(600):
                    cur = prev_state(cur)
                    states.append(cur)
                for k in range(0, 600):
                    key = key_from_rand_outputs(outputs_from(states[k], 16))
                    hits, det = score_key(key, packets)
                    if hits:
                        found = {'holdrand': holdrand,
                                 'state': si_value,
                                 'offset': k,
                                 'key': key.decode('ascii', 'replace'),
                                 'hits': hits, 'details': det}
                        log('*** KEY FOUND %s hits=%d offset=%d'
                            % (found['key'], hits, k))
                        break
                if found:
                    break
            if found and found['hits'] == len(packets):
                break
        time.sleep(0.01)

    if found:
        with open(os.path.join(args.out, 'aes_key_FOUND.json'), 'w',
                  encoding='utf-8') as fh:
            json.dump(found, fh, ensure_ascii=False, indent=2)
        log('KEY FOUND -> aes_key_FOUND.json')
    else:
        log('no key recovered; states=%d packets=%d'
            % (len(seen_states), len(packets)))
    stop.set()
    log('done pid=%d' % pid)
    logf.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
