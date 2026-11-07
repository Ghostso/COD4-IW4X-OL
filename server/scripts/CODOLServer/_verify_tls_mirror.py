#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify: engine dump (VA 0x994000..0xE65000) is a plaintext mirror of the
Base.dll .tls section (rva 0xB0A000, raw 0xAFF800, size 0xED2600).

If decrypted_jit == on_disk at the same rva, then the .tls "high entropy" bytes
are simply XOR-obfuscated at the same offset, and we can recover the transform
by comparing a few known-plaintext ASCII regions.
"""

import glob
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE_BASE = 0x00994000
TLS_RVA = 0x00B0A000
TLS_RAW = 0x00AFF800
TLS_SIZE = 0x00ED2600


def main():
    dll = open(os.path.join(ROOT, 'COD OL',
                            'codoMP_client_shipRetailBase.dll'), 'rb').read()
    dumps = sorted(glob.glob(os.path.join(
        ROOT, 'run_codol_001', 'runs', 'ENGINE_DUMP_*', 'engine',
        'engine_best.bin')))
    for dp in dumps:
        d = open(dp, 'rb').read()
        if not any(d[:4096]):
            print('%s: all-zero, skip' % os.path.relpath(dp, ROOT))
            continue
        print('== %s len=%d' % (os.path.relpath(dp, ROOT), len(d)))
        # sample several rvas inside .tls and compare
        for rva in (0x00D5A000, 0x00E40400, 0x00E44400, 0x00E48C00,
                    0x00D85A00, 0x01900000):
            if not (TLS_RVA <= rva < TLS_RVA + TLS_SIZE):
                continue
            doff = rva - ENGINE_BASE
            soff = TLS_RAW + (rva - TLS_RVA)
            if doff < 0 or doff + 32 > len(d) or soff + 32 > len(dll):
                print('   rva %08X  out of range' % rva)
                continue
            a = d[doff:doff + 32]
            b = dll[soff:soff + 32]
            same = sum(1 for x, y in zip(a, b) if x == y)
            xor = bytes(x ^ y for x, y in zip(a, b))
            print('   rva %08X dump=%s' % (rva, a.hex()))
            print('              dll =%s' % b.hex())
            print('              xor =%s  equal=%d/32' % (xor.hex(), same))


if __name__ == '__main__':
    main()
