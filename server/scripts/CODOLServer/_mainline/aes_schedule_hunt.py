#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aes_schedule_hunt.py -- find an AES key schedule in the live CODOL process
WITHOUT needing the 8081 ciphertext.

Idea: AES key expansion has a rigid structure. If we find 176/208/240 bytes
where the second half is exactly ExpandKey(first 16/24/32 bytes), we have
found a key schedule that the program actually built. That works even when
the key itself is derived at runtime and never stored contiguously.

Also reports any region containing the AES inverse S-box, which marks the
crypto module and therefore the code that uses the schedule.

Run elevated (through elevated_agent.py). Read-only.
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

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
MEM_COMMIT = 0x1000
PAGE_GUARD = 0x100
PAGE_NOACCESS = 0x01


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


def builtin_sbox():
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


SBOX = builtin_sbox()
INV_SBOX = bytes.fromhex(
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
RCON = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 0x36,
        0x6c, 0xd8, 0xab, 0x4d]


def expand_key(key):
    nk = len(key) // 4
    if nk not in (4, 6, 8):
        return None
    nr = nk + 6
    w = [list(key[4 * i:4 * i + 4]) for i in range(nk)]
    for i in range(nk, 4 * (nr + 1)):
        t = list(w[i - 1])
        if i % nk == 0:
            t = t[1:] + t[:1]
            t = [SBOX[b] for b in t]
            t[0] ^= RCON[i // nk - 1]
        elif nk > 6 and i % nk == 4:
            t = [SBOX[b] for b in t]
        w.append([w[i - nk][j] ^ t[j] for j in range(4)])
    return b''.join(bytes(x) for x in w)


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
    ap.add_argument('--time-limit', type=float, default=600.0)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    logf = open(os.path.join(args.out, 'schedule_hunt.log'), 'w',
                encoding='utf-8')

    def log(msg):
        logf.write(msg + '\n')
        logf.flush()
        print(msg, flush=True)

    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False,
                        args.pid)
    log('OpenProcess(%d) -> %s err=%d' % (args.pid, h, ctypes.get_last_error()))
    if not h:
        return 1

    t0 = time.time()
    found = []
    sbox_hits = []
    sched_ptrs = []
    n_regions = 0
    n_bytes = 0
    for base, size in regions(h):
        if time.time() - t0 > args.time_limit:
            log('time limit')
            break
        n_regions += 1
        off = 0
        while off < size:
            want = min(0x100000, size - off)
            data = read_some(h, base + off, want)
            if data:
                n_bytes += len(data)
                if len(sbox_hits) < 8 and INV_SBOX in data:
                    i = data.find(INV_SBOX)
                    sbox_hits.append(base + off + i)
                    log('AES INV SBOX at 0x%08X' % (base + off + i))
                scan_chunk(data, base + off, found, log)
            off += want
        if n_regions % 200 == 0:
            log('regions=%d bytes=%d schedules=%d t=%.0fs'
                % (n_regions, n_bytes, len(found), time.time() - t0))

    log('done regions=%d bytes=%d schedules=%d sbox_hits=%d'
        % (n_regions, n_bytes, len(found), len(sbox_hits)))
    with open(os.path.join(args.out, 'aes_schedules.jsonl'), 'w',
              encoding='utf-8') as fh:
        for f in found:
            fh.write(json.dumps(f, ensure_ascii=False) + '\n')
    with open(os.path.join(args.out, 'aes_sbox_hits.json'), 'w',
              encoding='utf-8') as fh:
        json.dump(sbox_hits, fh, indent=2)
    log('wrote aes_schedules.jsonl / aes_sbox_hits.json')
    return 0


def scan_chunk(data, va, found, log):
    """Look for a schedule whose tail equals ExpandKey(head).

    Fast pre-filter: w[4] must equal w[0] xor SubWord(RotWord(w[3])) xor Rcon.
    That single 4-byte equation rejects virtually all random data, so the full
    expansion is only computed for survivors.
    """
    n = len(data)
    sl = SBOX
    for off in range(0, n - 20, 4):
        w0 = data[off:off + 4]
        w3 = data[off + 12:off + 16]
        w4 = data[off + 16:off + 20]
        # RotWord(w3) = [w3[1], w3[2], w3[3], w3[0]], then SubWord, then Rcon.
        t0 = sl[w3[1]] ^ 0x01
        if w4[0] != w0[0] ^ t0:
            continue
        if w4[1] != w0[1] ^ sl[w3[2]]:
            continue
        if w4[2] != w0[2] ^ sl[w3[3]]:
            continue
        if w4[3] != w0[3] ^ sl[w3[0]]:
            continue
        # Survivor: full expansion check for 16/24/32 byte keys.
        for ksize, ssize in ((16, 176), (24, 208), (32, 240)):
            if off + ssize > n:
                continue
            head = bytes(data[off:off + ksize])
            if len(set(head)) < 6:
                continue
            try:
                sched = expand_key(head)
            except Exception:
                continue
            if sched is not None and data[off:off + ssize] == sched:
                rec = {'va': va + off, 'bits': ksize * 8,
                       'key': head.hex(), 'schedule_va': va + off,
                       'schedule_len': ssize}
                found.append(rec)
                log('SCHEDULE MATCH key=%s va=0x%08X bits=%d'
                    % (head.hex(), va + off, ksize * 8))


if __name__ == '__main__':
    sys.exit(main())
