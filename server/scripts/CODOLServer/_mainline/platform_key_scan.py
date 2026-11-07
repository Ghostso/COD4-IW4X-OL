#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
platform_key_scan.py -- read the unprotected platform processes (TQMCenter,
IIPSHostApp, CrossProxy) and recover the AES key used by the 8081 QoS channel.

The game process is ACE-protected; the platform processes are not. SSOPlatform
and CrossShell contain the AES/QoS implementation, so the key/schedule is
expected to live there.
"""

import argparse
import ctypes
import ctypes.wintypes as wt
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import aes_schedule_hunt as AS  # noqa: E402

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

k32 = ctypes.WinDLL('kernel32', use_last_error=True)

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
MEM_COMMIT = 0x1000
PAGE_GUARD = 0x100
PAGE_NOACCESS = 0x01

ALPHABET = 'ABCDEFGHIJKMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789'
PAT = re.compile(('[' + ALPHABET + ']{16}').encode())


class MBI(ctypes.Structure):
    _fields_ = [('BaseAddress', ctypes.c_void_p),
                ('AllocationBase', ctypes.c_void_p),
                ('AllocationProtect', wt.DWORD),
                ('RegionSize', ctypes.c_size_t),
                ('State', wt.DWORD), ('Protect', wt.DWORD),
                ('Type', wt.DWORD)]


k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p,
                                  ctypes.c_void_p, ctypes.c_size_t,
                                  ctypes.POINTER(ctypes.c_size_t)]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p,
                               ctypes.POINTER(MBI), ctypes.c_size_t]


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


def dec(key, block):
    d = Cipher(algorithms.AES(key), modes.ECB()).decryptor()
    return d.update(block) + d.finalize()


def test_key(key, packets):
    hits = 0
    details = []
    for i, p in enumerate(packets[:9]):
        body = p[:-4]
        if len(body) < 16:
            continue
        try:
            pt = dec(key, body[:16])
        except Exception:
            continue
        # Require a real QoS header shape, not just a magic pair, so random
        # alphanumeric strings cannot produce false positives.
        ok = pt[:2] in (b'ur', b'us', b'ru', b'su')
        if not ok and len(pt) >= 4:
            import struct as _s
            ok = (_s.unpack_from('>H', pt, 0)[0] in (16, 24)
                  and _s.unpack_from('>H', pt, 2)[0] < 4096)
        if ok:
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
    ap.add_argument('--pids', required=True,
                    help='comma-separated platform PIDs')
    ap.add_argument('--packets', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--time-limit', type=float, default=240.0)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    logf = open(os.path.join(args.out, 'platform_scan.log'), 'w',
                encoding='utf-8')

    def log(m):
        logf.write(m + '\n')
        logf.flush()
        print(m, flush=True)

    packets = load_packets(args.packets)
    log('packets=%d' % len(packets))
    if not packets:
        return 1

    all_found = []
    for pid_s in args.pids.split(','):
        pid = int(pid_s.strip())
        h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ,
                            False, pid)
        log('pid=%d handle=%s err=%d' % (pid, h, ctypes.get_last_error()))
        if not h:
            continue
        t0 = time.time()
        tested = set()
        schedules = []
        for base, size in regions(h):
            if time.time() - t0 > args.time_limit:
                break
            off = 0
            while off < size:
                want = min(0x100000, size - off)
                data = read_some(h, base + off, want)
                if data:
                    for m in PAT.finditer(data):
                        k = m.group()
                        if k in tested:
                            continue
                        tested.add(k)
                        hits, det = test_key(k, packets)
                        if hits:
                            rec = {'pid': pid, 'key': k.decode('ascii', 'replace'),
                                   'va': base + off + m.start(), 'hits': hits,
                                   'details': det}
                            log('MATCH alnum key=%s hits=%d va=0x%08X'
                                % (rec['key'], hits, rec['va']))
                            all_found.append(rec)
                    cand = []
                    AS.scan_chunk(data, base + off, cand, lambda m: None)
                    for c in cand:
                        k = bytes.fromhex(c['key'])
                        if k in tested:
                            continue
                        tested.add(k)
                        hits, det = test_key(k, packets)
                        if hits:
                            rec = {'pid': pid, 'key': c['key'],
                                   'va': c['va'], 'hits': hits,
                                   'details': det, 'source': 'schedule'}
                            log('MATCH schedule key=%s hits=%d va=0x%08X'
                                % (rec['key'], hits, rec['va']))
                            all_found.append(rec)
                off += want
        log('pid=%d tested=%d matches=%d'
            % (pid, len(tested), len(all_found)))
        k32.CloseHandle(h)

    if all_found:
        best = max(all_found, key=lambda r: r['hits'])
        with open(os.path.join(args.out, 'aes_key_FOUND.json'), 'w',
                  encoding='utf-8') as fh:
            json.dump(best, fh, ensure_ascii=False, indent=2)
        log('KEY FOUND -> aes_key_FOUND.json')
    else:
        log('no platform key found')
    return 0


if __name__ == '__main__':
    sys.exit(main())
