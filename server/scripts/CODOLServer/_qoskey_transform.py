#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Derive the .tls runtime transform from known plaintext, then test whether
the 8081 payloads use the same transform.

The engine dump is the runtime-instanced image of the .tls VA window
0x994000..0xE65000. On-disk section bytes at the identical rva are still
obfuscated. Known plaintext strings (e.g. SEMV/NUL padding) let us check
whether the relation is a per-position XOR, a stream cipher, or a page/table
transform.
"""

import os
import sys
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE_BASE = 0x00994000
TLS_RVA = 0x00B0A000
TLS_RAW = 0x00AFF800
TLS_SIZE = 0x00ED2600
DUMP = os.path.join(ROOT, 'run_codol_001', 'runs',
                    'ENGINE_DUMP_20260925_114204', 'engine', 'engine_best.bin')


def main():
    d = open(DUMP, 'rb').read()
    dll = open(os.path.join(ROOT, 'COD OL',
                            'codoMP_client_shipRetailBase.dll'), 'rb').read()
    print('dump_len=%d runtime_va=[%08X,%08X)' % (
        len(d), ENGINE_BASE, ENGINE_BASE + len(d)))

    # search the whole dump for SEMV
    off = 0
    hits = []
    while True:
        i = d.find(b'SEMV', off)
        if i < 0:
            break
        hits.append(i)
        off = i + 1
    print('SEMV hits:', ['0x%08X' % (ENGINE_BASE + i) for i in hits[:10]])

    for i in hits[:4]:
        va = ENGINE_BASE + i
        rva = va
        so = TLS_RAW + (rva - TLS_RVA)
        disk = dll[so:so + 64]
        run = d[i:i + 64]
        print('')
        print('SEMV at rva=0x%08X disk_off=0x%X' % (rva, so))
        print('  run :', run.hex())
        print('  disk:', disk.hex())
        xor = bytes(a ^ b for a, b in zip(run, disk))
        print('  xor :', xor.hex())
        # try repeating-period detection on the xor difference
        for per in range(1, 17):
            if all(xor[j] == xor[j % per] for j in range(len(xor))):
                print('  xor is periodic period=%d key=%s'
                      % (per, xor[:per].hex()))

    # Known plaintext from runtime QoS table: check whether disk is a simple
    # XOR stream by comparing >=64-byte runs of printable runtime data.
    print('')
    print('=== sample known runtime printable runs vs disk ===')
    for va in (0x00D5A0E8, 0x00D5A228, 0x00E4022C, 0x00E4444C,
               0x00E48C80, 0x00E49380):
        i = va - ENGINE_BASE
        so = TLS_RAW + (va - TLS_RVA)
        if i < 0 or i + 64 > len(d) or so + 64 > len(dll):
            continue
        run = d[i:i + 64]
        disk = dll[so:so + 64]
        xor = bytes(a ^ b for a, b in zip(run, disk))
        print('rva %08X disk_off %X run=%r' % (va, so, run[:48]))
        print('  xor=%s' % xor.hex())

    # Test the 8081 ciphertexts against common transformations:
    # 1) XOR with a 256-byte table built from disk/runtime difference
    # 2) XOR with a 1024-byte key = first 1024 bytes of runtime table
    import json
    pl = os.path.join(ROOT, 'run_codol_001', 'runs', 'SINGLE_V3',
                      'local_listeners.jsonl')
    pkts = []
    for line in open(pl, encoding='utf-8', errors='replace'):
        o = json.loads(line)
        if 'data_hex' in o:
            pkts.append(bytes.fromhex(o['data_hex']))

    print('')
    print('=== 8081 first bytes under candidate XOR keys ===')
    keys = {
        'ru-repeat': b'ru' * 64,
        'su-repeat': b'su' * 64,
        '0x356c4bc3-le': (0x356C4BC3).to_bytes(4, 'little') * 32,
        '0x356c4bc3-be': (0x356C4BC3).to_bytes(4, 'big') * 32,
        'ASCII356c4bc3': b'356c4bc3' * 16,
        'DW-Ticket-Seed': b'DW-Ticket-Seed\x00' * 8,
    }
    for name, k in keys.items():
        outs = []
        for p in pkts[:3]:
            o = bytes(a ^ b for a, b in zip(p, k))
            outs.append(repr(o[:16]))
        print('  %-16s %s' % (name, ' | '.join(outs)))


if __name__ == '__main__':
    main()
