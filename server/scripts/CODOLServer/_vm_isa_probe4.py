#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VM ISA probe 4: derive the on-disk -> runtime transform for a section,
and test whether it is a simple repeating XOR mask."""

import os
import collections
import pefile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DLL = os.path.join(ROOT, 'COD OL', 'codoMP_client_shipRetailBase.dll')
DUMP = os.path.join(ROOT, 'run_codol_001', 'runs',
                    'ENGINE_DUMP_20260925_114204', 'engine',
                    'engine_best.bin')
ENGINE_BASE = 0x00994000


def main():
    d = open(DLL, 'rb').read()
    e = open(DUMP, 'rb').read()
    pe = pefile.PE(data=d, fast_load=True)
    secs = {}
    for s in pe.sections:
        nm = s.Name.rstrip(b'\x00').decode('latin1')
        secs[nm] = (s.VirtualAddress, s.PointerToRawData, s.SizeOfRawData)

    tls_rva, tls_raw, tls_sz = secs['.tls']
    print('Testing transform: runtime[rva] vs disk[rva] inside .tls')
    print('(sample inside the engine window, which is a .tls subrange)')
    print('')

    # sample a few spots inside the engine window that belong to .tls
    tests = [0x00B0A000, 0x00C00000, 0x00C84C40, 0x00C90000, 0x00CA0000]
    for rva in tests:
        do = rva - ENGINE_BASE
        so = tls_raw + (rva - tls_rva)
        if do < 0 or do + 64 > len(e) or so + 64 > len(d):
            continue
        run = e[do:do + 64]
        disk = d[so:so + 64]
        x = bytes(a ^ b for a, b in zip(run, disk))
        print('rva %08X' % rva)
        print('  run : %s' % run.hex())
        print('  disk: %s' % disk.hex())
        print('  xor : %s' % x.hex())
        # look for 8-byte periodicity in the xor
        for per in (4, 8, 16):
            keys = [x[i:i + per] for i in range(0, len(x), per)]
            print('    period %2d distinct=%d' % (per, len(set(keys))))

    print('')
    print('=== global check: is disk->runtime a constant 8-byte XOR key? ===')
    # collect xor words over a wide sample
    counter = collections.Counter()
    samples = 0
    for rva in range(0x00B0A000, 0x00CA7890, 0x1000):
        if rva + 32 > tls_rva + tls_sz:
            break
        do = rva - ENGINE_BASE
        so = tls_raw + (rva - tls_rva)
        if do < 0 or do + 32 > len(e) or so + 32 > len(d):
            continue
        x = bytes(a ^ b for a, b in zip(e[do:do + 32], d[so:so + 32]))
        for i in range(0, 32, 8):
            counter[x[i:i + 8]] += 1
        samples += 1
    print('sampled %d pages' % samples)
    for key, cnt in counter.most_common(8):
        print('  8-byte block %s : %d' % (key.hex(), cnt))


if __name__ == '__main__':
    main()
