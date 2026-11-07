#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VM ISA probe 3: verify the 'disk is zero' premise and the .tls relation."""

import os
import hashlib
import pefile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DLL = os.path.join(ROOT, 'COD OL', 'codoMP_client_shipRetailBase.dll')
DUMP = os.path.join(ROOT, 'run_codol_001', 'runs',
                    'ENGINE_DUMP_20260925_114204', 'engine',
                    'engine_best.bin')
ENGINE_BASE = 0x00994000
ENGINE_END = 0x00CA7890


def main():
    d = open(DLL, 'rb').read()
    e = open(DUMP, 'rb').read()
    pe = pefile.PE(data=d, fast_load=True)
    secs = {}
    for s in pe.sections:
        nm = s.Name.rstrip(b'\x00').decode('latin1')
        secs[nm] = (s.VirtualAddress, s.PointerToRawData, s.SizeOfRawData)

    def rva_to_raw(rva):
        for nm, (rv, raw, sz) in secs.items():
            if rv <= rva < rv + sz:
                return raw + (rva - rv), nm
        return None, None

    print('=== is the engine window zero on disk? ===')
    for va in (0x00994000, 0x009A0000, 0x00A00000, 0x00B0A000,
               0x00C84C40, 0x00CA0000):
        raw, nm = rva_to_raw(va)
        disk = d[raw:raw + 64] if raw is not None else b''
        dop = va - ENGINE_BASE
        run = e[dop:dop + 64] if 0 <= dop < len(e) else b''
        print('%08X %-8s disk_off=0x%08X' % (va, nm, raw or 0))
        print('     disk    : %s' % disk.hex())
        print('     runtime : %s' % run.hex())
        print('     disk_all_zero=%s  runtime_all_zero=%s'
              % (set(disk) == {0}, set(run) == {0}))

    print('')
    print('=== .tls-wide zero fraction on disk ===')
    tls_rva, tls_raw, tls_sz = secs['.tls']
    disk_tls = d[tls_raw:tls_raw + tls_sz]
    print('.tls disk : zeros=%d/%d (%.1f%%)'
          % (disk_tls.count(0), len(disk_tls),
             100.0 * disk_tls.count(0) / len(disk_tls)))

    print('')
    print('=== runtime window coverage map ===')
    n = len(e)
    print('runtime covers rva [%08X,%08X)' % (ENGINE_BASE, ENGINE_BASE + n))
    first_nz = None
    last_nz = None
    nz_blocks = 0
    for o in range(0, n, 1 << 16):
        blk = e[o:o + (1 << 16)]
        if any(blk):
            nz_blocks += 1
            if first_nz is None:
                first_nz = o
            last_nz = o
    print('non-zero 64K blocks: %d / %d'
          % (nz_blocks, (n + 0xFFFF) // (1 << 16)))
    if first_nz is not None:
        print('first non-zero block rva %08X' % (ENGINE_BASE + first_nz))
        print('last  non-zero block rva %08X' % (ENGINE_BASE + last_nz))

    print('')
    print('=== does .tvm0 content appear in the runtime window? ===')
    tvm_rva, tvm_raw, tvm_sz = secs['.tvm0']
    sample = d[tvm_raw:tvm_raw + 4096]
    print('  .tvm0 first 4KB sha256=%s'
          % hashlib.sha256(sample).hexdigest()[:32])
    print('  present in runtime window: %s' % (sample in e))

    print('')
    print('=== section spans vs engine range 0x%08X..0x%08X ==='
          % (ENGINE_BASE, ENGINE_END))
    for nm, (rv, raw, sz) in sorted(secs.items(), key=lambda kv: kv[1][0]):
        lo, hi = rv, rv + sz
        ov = max(0, min(hi, ENGINE_END) - max(lo, ENGINE_BASE))
        print('  %-8s [%08X,%08X) overlap_with_engine=%d bytes'
              % (nm, lo, hi, ov))


if __name__ == '__main__':
    main()
