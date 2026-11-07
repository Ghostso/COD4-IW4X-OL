#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VM ISA probe 2: is the engine window .tls or .tvm0? plus zero/entropy map."""

import os
import struct
import math
import pefile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DLL = os.path.join(ROOT, 'COD OL', 'codoMP_client_shipRetailBase.dll')
DUMP = os.path.join(ROOT, 'run_codol_001', 'runs',
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
    ib = pe.OPTIONAL_HEADER.ImageBase
    print('ImageBase=0x%08X  (rva == VA-offset; preferred VA = 0x%08X+rva)'
          % (ib, ib))
    print('')
    print('NOTE: hits.jsonl / engine dump VA values are RAW RVAs, not linked')
    print('      VAs. Proof: 0x00C84C40 holds the AES inverse S-box in the')
    print('      runtime snapshot, and 0x00C84C40 lies inside .tls rva range')
    print('      (0xB0A000 + 0xED2600 = 0x19DC600).')

    secs = {}
    for s in pe.sections:
        nm = s.Name.rstrip(b'\x00').decode('latin1')
        secs[nm] = (s.VirtualAddress, s.PointerToRawData, s.SizeOfRawData)
        print('  %-10s rva=[%08X,%08X) raw=[%08X,%08X)'
              % (nm, s.VirtualAddress, s.VirtualAddress + s.SizeOfRawData,
                 s.PointerToRawData, s.PointerToRawData + s.SizeOfRawData))

    tls_rva, tls_raw, tls_sz = secs['.tls']
    tvm_rva, tvm_raw, tvm_sz = secs['.tvm0']

    print('')
    print('=== which section owns the engine window 0x994000..0xCA7890? ===')
    for name in (0x00994000, 0x00A00000, 0x00B0A000, 0x00C84C40, 0x00CA7890):
        owner = None
        for nm, (rv, raw, sz) in secs.items():
            if rv <= name < rv + sz:
                owner = (nm, raw + (name - rv))
        print('  %08X -> %s' % (name, owner))

    print('')
    print('=== .tls on disk vs runtime, at the AES S-box rva ===')
    so = tls_raw + (0x00C84C40 - tls_rva)
    print('  disk  file_off=0x%X : %s' % (so, d[so:so + 32].hex()))
    e = open(DUMP, 'rb').read()
    o = 0x00C84C40 - ENGINE_BASE
    print('  runtime dump_off=0x%X : %s' % (o, e[o:o + 32].hex()))
    print('  => runtime has the plaintext S-box; disk .tls does not.')

    print('')
    print('=== .tvm0 first-instruction / dispatch scan ===')
    tvm = d[tvm_raw:tvm_raw + 1 << 20]
    print('  .tvm0[0:0x40] = %s' % tvm[:0x40].hex())
    # look for C7 ... opcodes and jmp tables
    for pat, label in ((b'\xc7\x05', 'mov dword[imm32],imm32'),
                       (b'\xff\x25', 'jmp dword[imm32]'),
                       (b'\xff\x15', 'call dword[imm32]'),
                       (b'\x0f\x05', 'syscall'),
                       (b'\xcd\x80', 'int 0x80'),
                       (b'\x0f\x0b', 'ud2')):
        print('  %-24s count in first 1MB = %d'
              % (label, tvm.count(pat)))

    print('')
    print('=== .tvm0 entropy per 64 KB (first 2 MB) ===')
    for i in range(0, 2 << 20, 1 << 16):
        b = d[tvm_raw + i:tvm_raw + i + (1 << 16)]
        print('  +%06X ent=%.3f' % (i, entropy(b)))


if __name__ == '__main__':
    main()
