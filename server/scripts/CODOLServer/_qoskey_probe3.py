#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe 3: raw-hex reconstruction of the Demonware/Blaze auth+ticket constant
cluster and the qos_cs / qos_ss module tables.

The hits.jsonl 'text' field is already a lossy (non-printable -> '.') view.
For byte-exact work we re-scan the loaded module bytes from disk at the same
RVA and print real hex.
"""

import hashlib
import os
import struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DLL = os.path.join(ROOT, 'COD OL', 'codoMP_client_shipRetailBase.dll')

# The hits.jsonl 'va' values for this module are file/RVA offsets directly
# (verified: 0x00D5A0EC lands inside .tls rva 0x00B0A000 .. 0x019DD000).
IMAGEBASE = 0


def rva(va):
    return va & 0xFFFFFFFF


def hexdump(b, base_va, width=16):
    out = []
    for off in range(0, len(b), width):
        row = b[off:off + width]
        hx = ' '.join('%02x' % c for c in row)
        asc = ''.join(chr(c) if 32 <= c < 127 else '.' for c in row)
        out.append('%08X  %-47s  %s' % (base_va + off, hx, asc))
    return '\n'.join(out)


def main():
    pe = None
    d = open(BASE_DLL, 'rb').read()
    print('Base.dll size=%d sha256=%s' % (len(d),
                                          hashlib.sha256(d).hexdigest()[:32]))

    import pefile
    pe = pefile.PE(data=d, fast_load=True)
    ib = pe.OPTIONAL_HEADER.ImageBase
    print('ImageBase=0x%08X  (hits VAs are file/RVA offsets)' % ib)
    secs = []
    for s in pe.sections:
        nm = s.Name.rstrip(b'\x00').decode('latin1')
        secs.append((nm, s.VirtualAddress, s.PointerToRawData, s.SizeOfRawData,
                     s.Misc_VirtualSize))
        print('  %-10s rva=%08X raw=%08X rawsz=%08X vsz=%08X'
              % (nm, s.VirtualAddress, s.PointerToRawData, s.SizeOfRawData,
                 s.Misc_VirtualSize))

    def va_to_off(va):
        r = rva(va)
        for nm, rv, raw, rawsz, vsz in secs:
            if rv <= r < rv + max(rawsz, vsz):
                return raw + (r - rv), nm
        return None, None

    targets = [
        ('auth_task cluster', 0x00D5A210, 0x100),
        ('iv_seed / ticket', 0x00D5A0E0, 0xE0),
        ('server/client ticket + 356c4bc3', 0x00D5A2C0, 0x120),
        ('cd_key / auth url', 0x00D5A2C0, 0x80),
        ('qos_ss table', 0x00E40400, 0x80),
        ('qos_cs table', 0x00E444C0, 0x80),
        ('qos schema strings', 0x00E4937C, 0x180),
    ]
    for name, va, n in targets:
        off, sec = va_to_off(va)
        print('')
        print('=== %s  VA=0x%08X  rva=0x%08X  file_off=0x%X  sec=%s'
              % (name, va, rva(va), off or 0, sec))
        if off is None:
            print('   NOT IN FILE')
            continue
        print(hexdump(d[off:off + n], va))


if __name__ == '__main__':
    main()
