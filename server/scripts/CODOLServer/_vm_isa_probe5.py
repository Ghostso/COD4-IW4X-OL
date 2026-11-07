#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VM ISA probe 5: characterize the .tls on-disk obfuscation keystream.

Hypotheses tested:
  H1  fixed 8-byte repeating key                 -> refuted (probe4)
  H2  keystream indexed by 8-byte block number   (CTR/ECB-like)
  H3  key is a function of the block index only  (dedup: same idx, same key)
"""

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
    secs = {s.Name.rstrip(b'\x00').decode('latin1'):
            (s.VirtualAddress, s.PointerToRawData, s.SizeOfRawData)
            for s in pe.sections}
    tls_rva, tls_raw, tls_sz = secs['.tls']

    print('=== H2/H3: is the mask a function of the .tls block index? ===')
    # For a given .tls-relative 8-byte block index, the mask should be the
    # same regardless of which sub-page we look at -- but each rva maps to
    # exactly one index, so instead test: mask low16 distribution and
    # whether neighbouring blocks look like a counter-derived stream.
    masks = []
    for i in range(0, 64):
        rva = 0x00B0A000 + i * 8
        do = rva - ENGINE_BASE
        so = tls_raw + (rva - tls_rva)
        masks.append(bytes(a ^ b for a, b in
                           zip(e[do:do + 8], d[so:so + 8])))
    print('first 64 masks (tls-relative blocks):')
    for i, m in enumerate(masks):
        print('  blk %3d  %s' % (i, m.hex()))

    print('')
    print('=== is disk data independent of runtime (=true stream)? ===')
    # If it were a stream cipher over a *plaintext* .tls, runtime would be
    # plaintext and disk = plaintext ^ stream.  Check whether the runtime
    # bytes are plausible x86 code (high opcode density).
    txt = e[0x00B0A000 - ENGINE_BASE: 0x00B0A000 - ENGINE_BASE + 4096]
    common = collections.Counter(txt)
    print('runtime@B0A000 top bytes:',
          [(hex(k), v) for k, v in common.most_common(8)])
    prologues = txt.count(b'\x55\x8b\xec')
    ccs = txt.count(b'\xcc\xcc\xcc\xcc')
    print('  55 8B EC prologues=%d   CC padding runs=%d' % (prologues, ccs))

    print('')
    print('=== does .tls runtime region contain a reloc-applied image? ===')
    nz = 0
    for rva in range(0x00B0A000, 0x00CA7890, 0x1000):
        do = rva - ENGINE_BASE
        if do + 16 > len(e):
            break
        if any(e[do:do + 16]):
            nz += 1
    print('pages with data in [B0A000,CA7890): %d' % nz)

    print('')
    print('=== per-page mask sample (page 0, mid, last) ===')
    for rva in (0x00B0A000, 0x00C00000, 0x00CA7000):
        do = rva - ENGINE_BASE
        so = tls_raw + (rva - tls_rva)
        if do < 0 or do + 16 > len(e) or so + 16 > len(d):
            continue
        print('  rva %08X run=%s disk=%s'
              % (rva, e[do:do + 16].hex(), d[so:so + 16].hex()))


if __name__ == '__main__':
    main()
