#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe 5 (final): (a) .tls runtime mirror extent, (b) handoff block scan,
(c) the QoS magic literals, (d) QOS_SS vs QOS_CS magic widths."""

import glob
import os
import struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE_BASE = 0x00994000
DUMP = os.path.join(ROOT, 'run_codol_001', 'runs',
                    'ENGINE_DUMP_20260925_114204', 'engine', 'engine_best.bin')


def main():
    d = open(DUMP, 'rb').read()
    print('dump %s len=%d  VA range 0x%08X..0x%08X'
          % (os.path.relpath(DUMP, ROOT), len(d), ENGINE_BASE,
             ENGINE_BASE + len(d)))

    # (a) largest decorated/stack VA range covered by this window, so we know
    # which .tls rva span the loader has instantiated.
    print('')
    print('=== highest window VA = 0x%08X ===' % (ENGINE_BASE + len(d)))

    # locate a page whose first dword is a plausible VA pattern
    for probe in (0x00D5A000, 0x00D85A00, 0x00E40400, 0x00E44400,
                  0x00E48C00, 0x00E65000):
        o = probe - ENGINE_BASE
        if 0 <= o < len(d):
            print('  rva 0x%08X present (off 0x%X)' % (probe, o))
        else:
            print('  rva 0x%08X NOT in window' % probe)

    # (b) is there a 1964-byte TCLS handoff-like block?
    print('')
    print('=== search for TCLS handoff signatures in the 5 MB window ===')
    for pat in (b'TCLS', b'TSP', b'QRY', b'RSP', b'TCLS_SHAREDMEMEMORY',
                b'gameSignature', b'g.a.m.e.S', b'SEMV'):
        offs = []
        s = 0
        while len(offs) < 8:
            i = d.find(pat, s)
            if i < 0:
                break
            offs.append(i)
            s = i + 1
        if offs:
            print('  %-24s %s' % (pat.decode('latin1'),
                                  ', '.join('0x%08X' % (ENGINE_BASE + o)
                                            for o in offs)))

    # (c) QoS magic literals around the tables
    print('')
    print('=== bytes immediately PRECEDING qos_cs / qos_ss labels ===')
    for label, va in (('qos_cs', 0x00E444EC), ('qos_ss', 0x00E4042C)):
        o = va - ENGINE_BASE
        chunk = d[o - 0xB0:o]
        print('  %s: %s' % (label, chunk.hex()))

    # (d) QOS_CS_MAGIC / QOS_SS_MAGIC name-pool preambles
    print('')
    print('=== name-pool preamble (16 dwords before the literal) ===')
    for label, va in (('QOS_CS_MAGIC', 0x00E48C80),
                      ('QOS_SS_MAGIC', 0x00E43DE0)):
        o = va - ENGINE_BASE
        words = struct.unpack_from('<16I', d, o - 0x40)
        print('  %s: %s' % (label, ' '.join('%08X' % w for w in words)))


if __name__ == '__main__':
    main()
