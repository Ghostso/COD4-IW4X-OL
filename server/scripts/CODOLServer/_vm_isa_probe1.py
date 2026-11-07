#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VM ISA probe 1: PE layout, .tvm0 structure, engine-base write refs.

Read-only static analysis of codoMP_client_shipRetailBase.dll plus the
existing runtime engine snapshot.
"""

import os
import re
import struct
import math
import pefile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DLL = os.path.join(ROOT, 'COD OL', 'codoMP_client_shipRetailBase.dll')
ENGINE = os.path.join(ROOT, 'run_codol_001', 'runs',
                      'ENGINE_DUMP_20260925_114204', 'engine',
                      'engine_best.bin')
ENGINE_BASE = 0x00994000


def entropy(b):
    if not b:
        return 0.0
    c = [0] * 256
    for x in b:
        c[x] += 1
    n = float(len(b))
    return -sum((k / n) * math.log(k / n, 2) for k in c if k)


def main():
    d = open(DLL, 'rb').read()
    pe = pefile.PE(data=d, fast_load=True)
    print('DLL size=%d imagebase=0x%08X entry=0x%08X'
          % (len(d), pe.OPTIONAL_HEADER.ImageBase,
             pe.OPTIONAL_HEADER.AddressOfEntryPoint))
    secs = []
    for s in pe.sections:
        nm = s.Name.rstrip(b'\x00').decode('latin1')
        raw = s.PointerToRawData
        sz = s.SizeOfRawData
        body = d[raw:raw + sz]
        secs.append((nm, s.VirtualAddress, raw, sz, body))
        print('%-10s rva=%08X raw=%08X size=%08X ent=%.3f zeros=%d'
              % (nm, s.VirtualAddress, raw, sz, entropy(body[:1 << 20]),
                 body.count(0)))

    tvm = next(x for x in secs if x[0] == '.tvm0')
    nm, rva, raw, sz, body = tvm
    print('')
    print('=== .tvm0 head ===')
    for off in range(0, 256, 16):
        row = body[off:off + 16]
        print('%08X  %-47s  %s' % (rva + off,
                                   ' '.join('%02x' % c for c in row),
                                   ''.join(chr(c) if 32 <= c < 127 else '.'
                                           for c in row)))

    # ASCII strings
    print('')
    print('=== .tvm0 ASCII strings (>=8, sample) ===')
    seen = []
    for m in re.finditer(rb'[ -~]{8,}', body):
        s = m.group().decode('latin1')
        if len(seen) < 80:
            seen.append((rva + m.start(), s))
    for va, s in seen:
        print('  %08X  %s' % (va, s[:100]))

    # engine base constants referenced as absolute dwords
    print('')
    print('=== absolute dword refs into 0x994000..0xCA7890 ===')
    vals = [0x00994000, 0x00995000, 0x009A0000, 0x00A00000,
            0x00B00000, 0x00C00000, 0x00CA0000, 0x00CA7890]
    for target in vals:
        pat = struct.pack('<I', target)
        hits = []
        for secname, srva, sraw, ssz, sbody in secs:
            pos = 0
            while True:
                i = sbody.find(pat, pos)
                if i < 0:
                    break
                hits.append((secname, srva + i))
                pos = i + 1
                if len(hits) > 20:
                    break
        if hits:
            print('  0x%08X: %s' % (target,
                                    ['%s@%08X' % h for h in hits[:20]]))

    # find relative references to engine range in 32-bit displacements
    print('')
    print('=== near-ref dwords that point into 0x994000..0xCA7890 ===')
    found = []
    for secname, srva, sraw, ssz, sbody in secs:
        if secname == '.reloc':
            continue
        for off in range(0, len(sbody) - 4, 4):
            v = struct.unpack_from('<I', sbody, off)[0]
            if 0x00994000 <= v <= 0x00CA7890:
                found.append((secname, srva + off, v))
    for sec, va, v in found[:120]:
        print('  %-8s va=%08X -> %08X' % (sec, va, v))
    print('total', len(found))

    # AES S-box refs
    print('')
    print('=== refs to AES inverse S-box / nearby constants ===')
    for target in (0x00C84C40, 0x00C84C00, 0x00C84D40, 0x00C84E40):
        pat = struct.pack('<I', target)
        hits = []
        for secname, srva, sraw, ssz, sbody in secs:
            pos = 0
            while True:
                i = sbody.find(pat, pos)
                if i < 0:
                    break
                hits.append((secname, srva + i))
                pos = i + 1
        if hits:
            print('  0x%08X: %s' % (target,
                                    ['%s@%08X' % h for h in hits[:30]]))

    # runtime snapshot around AES table
    print('')
    if os.path.exists(ENGINE):
        e = open(ENGINE, 'rb').read()
        for target in (0x00C84C40, 0x00CA7890, 0x00C84C00):
            o = target - ENGINE_BASE
            print('=== runtime 0x%08X dump_off=0x%X ===' % (target, o))
            if 0 <= o < len(e):
                for j in range(0, 96, 16):
                    row = e[o + j:o + j + 16]
                    print('%08X  %-47s  %s'
                          % (target + j,
                             ' '.join('%02x' % c for c in row),
                             ''.join(chr(c) if 32 <= c < 127 else '.'
                                     for c in row)))


if __name__ == '__main__':
    main()
