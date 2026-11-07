#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe 4: byte-exact runtime view of the QoS tables from engine dumps."""

import glob
import hashlib
import os
import struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE_BASE = 0x00994000
DUMPS = os.path.join(ROOT, 'run_codol_001', 'runs')


def dump_paths():
    out = []
    for pat in ('ENGINE_DUMP_*/engine/engine_best.bin',
                'ENGINE_ATTACH_*/engine/engine_best.bin'):
        out += sorted(glob.glob(os.path.join(DUMPS, pat)))
    return out


def hexdump(b, base_va, width=16):
    for off in range(0, len(b), width):
        row = b[off:off + width]
        print('%08X  %-47s  %s' % (
            base_va + off, ' '.join('%02x' % c for c in row),
            ''.join(chr(c) if 32 <= c < 127 else '.' for c in row)))


def regions():
    # (label, VA, before, after)
    return [
        ('qos_cs label/table', 0x00E444EC, 0x140, 0x180),
        ('qos_ss label/table', 0x00E4042C, 0x140, 0x180),
        ('QOS_CS_MAGIC name pool', 0x00E48C80, 0x120, 0x200),
        ('QOS_SS_MAGIC name pool', 0x00E43DE0, 0x120, 0x200),
        ('QoS schema names', 0x00E49380, 0x80, 0x260),
        ('ticket/iv_seed/localhost defaults', 0x00D5A0E0, 0x60, 0x320),
        ('qos code strings', 0x00D85AE0, 0x40, 0x120),
    ]


def main():
    dumps = dump_paths()
    data = {}
    for p in dumps:
        b = open(p, 'rb').read()
        data[p] = b
        print('%s len=%d ent_hex=%s' % (
            os.path.relpath(p, ROOT), len(b),
            hashlib.sha256(b).hexdigest()[:16]))

    # prefer the largest nonzero dump
    cand = [(len(b), p, b) for p, b in data.items()
            if b and any(b)]
    cand.sort(reverse=True)
    p, b = cand[0][1], cand[0][2]
    print('using', os.path.relpath(p, ROOT))

    for label, va, before, after in regions():
        off = va - ENGINE_BASE
        print('')
        print('=== %s  va=0x%08X  dump_off=0x%X' % (label, va, off))
        if off < before or off + after > len(b):
            print('   OUT OF DUMP')
            continue
        hexdump(b[off - before:off + after], va - before)

    # compare candidate table bytes between the two runtime dumps
    if len(cand) >= 2:
        p2, b2 = cand[1][1], cand[1][2]
        if b2:
            print('')
            print('=== change check %s vs %s ===' % (
                os.path.relpath(p, ROOT), os.path.relpath(p2, ROOT)))
            for label, va, n in [('qos_cs', 0x00E44400, 0x100),
                                 ('qos_ss', 0x00E40400, 0x100),
                                 ('QOS_CS_MAGIC', 0x00E48C00, 0x100),
                                 ('tickets', 0x00D5A0E0, 0x280)]:
                o = va - ENGINE_BASE
                if o < 0 or o + n > min(len(b), len(b2)):
                    continue
                diff = sum(1 for x, y in zip(b[o:o + n], b2[o:o + n])
                           if x != y)
                print('  %-16s %d/%d bytes differ' % (label, diff, n))

    # decode LE32 tables around the qos labels
    print('')
    print('=== LE32 words around qos_cs label ===')
    o = 0x00E444EC - ENGINE_BASE
    for off in range(o - 0x80, o + 0x20, 4):
        v = struct.unpack_from('<I', b, off)[0]
        print('  va=%08X  %08X  %d' % (ENGINE_BASE + off, v, v))


if __name__ == '__main__':
    main()
