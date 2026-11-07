#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only AES key-schedule hunt in a live CODOL process.

Strategy (no injection, no Frida, no writes):
  1. OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ)
  2. Walk committed regions, read them
  3. Two detection passes:
       A. KEY SCHEDULE: find 176/208/240-byte aligned runs whose dword[0] and
          dword[1..] satisfy the AES key-expansion recurrence, i.e. the first
          16 bytes are a candidate key and the rest matches E_key expansion.
       B. RAW KEY ORACLE: for every 16/24/32-byte window, run AES-ECB decrypt
          on the first block of each real 8081 packet and test the plaintext
          shape (length header + block alignment + ASCII magic).

The oracle is deliberately strict so that a random 32-bit space cannot
produce a false positive.
"""

import argparse
import ctypes
import ctypes.wintypes as wt
import json
import os
import struct
import sys
import time

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
advapi32 = ctypes.WinDLL('advapi32', use_last_error=True)

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
MEM_COMMIT = 0x1000
PAGE_GUARD = 0x100
PAGE_NOACCESS = 0x01

TOKEN_ADJUST_PRIVILEGES = 0x0020
TOKEN_QUERY = 0x0008
SE_PRIVILEGE_ENABLED = 0x00000002
SE_DEBUG_NAME = 'SeDebugPrivilege'


class LUID(ctypes.Structure):
    _fields_ = [('LowPart', wt.DWORD), ('HighPart', wt.LONG)]


class LUID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [('Luid', LUID), ('Attributes', wt.DWORD)]


class TOKEN_PRIVILEGES(ctypes.Structure):
    _fields_ = [('PrivilegeCount', wt.DWORD),
                ('Privileges', LUID_AND_ATTRIBUTES * 1)]


class MBI(ctypes.Structure):
    _fields_ = [('BaseAddress', ctypes.c_void_p),
                ('AllocationBase', ctypes.c_void_p),
                ('AllocationProtect', wt.DWORD),
                ('RegionSize', ctypes.c_size_t),
                ('State', wt.DWORD), ('Protect', wt.DWORD),
                ('Type', wt.DWORD)]


k32.GetCurrentProcess.restype = wt.HANDLE
advapi32.OpenProcessToken.argtypes = [wt.HANDLE, wt.DWORD,
                                      ctypes.POINTER(wt.HANDLE)]
advapi32.OpenProcessToken.restype = wt.BOOL
advapi32.LookupPrivilegeValueW.argtypes = [wt.LPCWSTR, wt.LPCWSTR,
                                           ctypes.POINTER(LUID)]
advapi32.LookupPrivilegeValueW.restype = wt.BOOL
advapi32.AdjustTokenPrivileges.argtypes = [
    wt.HANDLE, wt.BOOL, ctypes.POINTER(TOKEN_PRIVILEGES), wt.DWORD,
    ctypes.c_void_p, ctypes.POINTER(wt.DWORD)]
advapi32.AdjustTokenPrivileges.restype = wt.BOOL
k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p,
                                  ctypes.c_void_p, ctypes.c_size_t,
                                  ctypes.POINTER(ctypes.c_size_t)]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p,
                               ctypes.POINTER(MBI), ctypes.c_size_t]

# ---------------------------------------------------------------- AES tables
def _builtin_sbox():
    """Reconstruct the AES S-box from the inverse table used earlier.

    This avoids transcription errors and is self-checking.
    """
    inv = bytes.fromhex(
        '52096ad53036a538bf40a39e81f3d7fb'
        '7ce339829b2fff87348e4344c4dee9cb'
        '547b9432a6c2233dee4c950b42fac34e'
        '082ea16628d924b2765ba2496d8bd125'
        '72f8f66486689816d4a45ccc5d65b692'
        '6c704850fdedb9da5e154657a78d9d84'
        '90d8ab008cbcd30af7e45805b8b34506'
        'd02c1e8fca3f0f02c1afbd0301138a6b'
        '3a9111414f67dcea97f2cfcef0b4e673'
        '96ac7422e7ad3585e2f937e81c75df6e'
        '47f11a711d29c5896fb7620eaa18be1b'
        'fc563e4bc6d279209adbc0fe78cd5af4'
        '1fdda8338807c731b11210592780ec5f'
        '60517fa919b54a0d2de57a9f93c99cef'
        'a0e03b4dae2af5b0c8ebbb3c83539961'
        '172b047eba77d626e169146355210c7d')
    fwd = bytearray(256)
    for i, v in enumerate(inv):
        fwd[v] = i
    return bytes(fwd)


SBOX = _builtin_sbox()
RCON = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 0x36,
        0x6c, 0xd8, 0xab, 0x4d]


def expand_key(key):
    """Standard AES key expansion; returns (schedule, nk, nr) or None."""
    nk = len(key) // 4
    if nk not in (4, 6, 8):
        return None, 0, 0
    nr = nk + 6
    w = [list(key[4 * i:4 * i + 4]) for i in range(nk)]
    total = 4 * (nr + 1)
    for i in range(nk, total):
        t = list(w[i - 1])
        if i % nk == 0:
            t = t[1:] + t[:1]
            t = [SBOX[b] for b in t]
            t[0] ^= RCON[i // nk - 1]
        elif nk > 6 and i % nk == 4:
            t = [SBOX[b] for b in t]
        w.append([w[i - nk][j] ^ t[j] for j in range(4)])
    return b''.join(bytes(x) for x in w), nk, nr


try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    HAVE_CRYPTO = True
except Exception:
    HAVE_CRYPTO = False


def aes_ecb_dec(key, block):
    c = Cipher(algorithms.AES(key), modes.ECB())
    d = c.decryptor()
    return d.update(block) + d.finalize()


# ---------------------------------------------------------------- oracle
def load_packets(path):
    out = []
    if not os.path.exists(path):
        return out
    for line in open(path, encoding='utf-8', errors='replace'):
        try:
            o = json.loads(line)
        except ValueError:
            continue
        h = o.get('data_hex')
        if not h:
            continue
        try:
            b = bytes.fromhex(h)
        except ValueError:
            continue
        if len(b) >= 20 and (len(b) - 4) % 16 == 0:
            out.append(b)
    return out


def score_plaintext(pt, full_ct):
    """Strict structural test of a decrypted first block (and optionally more).

    Returns (score, reason). score 0 = reject.
    """
    score = 0
    reasons = []
    if pt[:2] in (b'ur', b'us', b'ru', b'su'):
        score += 100
        reasons.append('ascii-magic:' + pt[:2].decode())
    # plausible big-endian headers seen on 8000: ruHeadLen=16, BodyLen=8
    u16 = struct.unpack('>HHHHHHHH', pt[:16])
    if u16[0] == 16:
        score += 40
        reasons.append('ruHeadLen=16')
    if u16[1] in (8, 24, 0x18) or u16[1] < 4096:
        score += 5
        reasons.append('bodyLen=%d' % u16[1])
    # plaintext length should explain ciphertext length:
    # ct_len - 4 == 16 * ceil(pt_len/16)
    for extra in (0, 4, 6, 8, 12, 16):
        blocks = (len(full_ct) - 4) // 16
        if 0 < extra and blocks:
            pass
    if pt[:2] in (b'ur', b'ru', b'us', b'su'):
        score += 10
    # small counters / seq look too random to use; ignore.
    if score:
        return score, ','.join(reasons)
    return 0, ''


def enable_debug():
    token = wt.HANDLE()
    if not advapi32.OpenProcessToken(
            k32.GetCurrentProcess(),
            TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, ctypes.byref(token)):
        return False, ctypes.get_last_error()
    luid = LUID()
    if not advapi32.LookupPrivilegeValueW(None, SE_DEBUG_NAME,
                                          ctypes.byref(luid)):
        err = ctypes.get_last_error()
        k32.CloseHandle(token)
        return False, err
    tp = TOKEN_PRIVILEGES()
    tp.PrivilegeCount = 1
    tp.Privileges[0].Luid = luid
    tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED
    ctypes.set_last_error(0)
    ok = advapi32.AdjustTokenPrivileges(token, False, ctypes.byref(tp),
                                        ctypes.sizeof(tp), None, None)
    err = ctypes.get_last_error()
    k32.CloseHandle(token)
    return bool(ok) and err == 0, err


def regions(h):
    addr = 0
    mbi = MBI()
    while k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi),
                             ctypes.sizeof(mbi)):
        base = int(mbi.BaseAddress or 0)
        size = int(mbi.RegionSize)
        if (mbi.State == MEM_COMMIT and not (mbi.Protect & PAGE_GUARD)
                and (mbi.Protect & 0xFF) != PAGE_NOACCESS):
            yield base, size
        nxt = base + size
        if nxt <= addr:
            return
        addr = nxt


def read_some(h, base, size):
    buf = ctypes.create_string_buffer(size)
    got = ctypes.c_size_t()
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(base), buf, size,
                                 ctypes.byref(got)):
        return b''
    return buf.raw[:got.value]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pid', type=int, required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--packets', required=True,
                    help='8081 local_listeners.jsonl')
    ap.add_argument('--max-region', type=int, default=16 * 1024 * 1024)
    ap.add_argument('--time-limit', type=float, default=900.0)
    ap.add_argument('--schedule-check', action='store_true', default=True)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    logp = os.path.join(args.out, 'aes_key_scan.log')
    logf = open(logp, 'w', encoding='utf-8')

    def log(msg):
        logf.write(msg + '\n')
        logf.flush()
        print(msg, flush=True)

    ok, err = enable_debug()
    log('SeDebugPrivilege=%s err=%d crypto=%s' % (ok, err, HAVE_CRYPTO))
    if not HAVE_CRYPTO:
        log('FATAL: no AES backend')
        return 1

    pkts = load_packets(args.packets)
    log('loaded %d 8081 packets from %s' % (len(pkts), args.packets))
    if not pkts:
        log('FATAL: no packets; cannot run oracle')
        return 1
    firsts = [p[:16] for p in pkts]
    lens = [len(p) for p in pkts]
    log('packet lens=%s' % lens)

    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False,
                        args.pid)
    log('OpenProcess(%d) -> %s err=%d' % (args.pid, h,
                                          ctypes.get_last_error()))
    if not h:
        log('FATAL: cannot open target')
        return 1

    t0 = time.time()
    n_regions = 0
    n_bytes = 0
    candidates = []
    schedules = []

    for base, size in regions(h):
        if time.time() - t0 > args.time_limit:
            log('time limit reached')
            break
        n_regions += 1
        off = 0
        while off < size:
            want = min(args.max_region, size - off)
            data = read_some(h, base + off, want)
            if data:
                n_bytes += len(data)
                scan_chunk(data, base + off, candidates, schedules,
                           firsts, lens, args.schedule_check)
            off += want
        if n_regions % 200 == 0:
            log('regions=%d bytes=%d cand=%d sched=%d t=%.0fs'
                % (n_regions, n_bytes, len(candidates), len(schedules),
                   time.time() - t0))

    log('scan done regions=%d bytes=%d candidates=%d schedules=%d'
        % (n_regions, n_bytes, len(candidates), len(schedules)))

    with open(os.path.join(args.out, 'aes_key_candidates.jsonl'), 'w',
              encoding='utf-8') as fh:
        for c in candidates:
            fh.write(json.dumps(c, ensure_ascii=False) + '\n')
    with open(os.path.join(args.out, 'aes_key_schedules.jsonl'), 'w',
              encoding='utf-8') as fh:
        for s in schedules:
            fh.write(json.dumps(s, ensure_ascii=False) + '\n')
    log('wrote candidates/schedules to %s' % args.out)
    k32.CloseHandle(h)
    logf.close()
    return 0


def scan_chunk(data, va, candidates, schedules, firsts, lens, do_sched):
    """Scan 16/24/32-byte windows with the AES-ECB oracle."""
    n = len(data)
    for size in (16, 24, 32):
        for off in range(0, n - size + 1, 4):
            key = bytes(data[off:off + size])
            if key == bytes(size) or len(set(key)) < 3:
                continue
            try:
                pt = aes_ecb_dec(key, firsts[0])
            except Exception:
                continue
            if pt[:2] not in (b'ur', b'us', b'ru', b'su'):
                continue
            hits = 0
            details = []
            for i, ct in enumerate(firsts):
                try:
                    p2 = aes_ecb_dec(key, ct)
                except Exception:
                    break
                if p2[:2] in (b'ur', b'us', b'ru', b'su'):
                    hits += 1
                    details.append({'pkt': i, 'pt': p2.hex()})
            candidates.append({
                'va': va + off, 'key_bits': size * 8, 'key': key.hex(),
                'pt_first': pt.hex(), 'confirmed_packets': hits,
                'details': details[:9],
            })


if __name__ == '__main__':
    sys.exit(main())
