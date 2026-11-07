#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_tqos_probe.py -- infer QOSCSPkgHead / QOSGetReq field widths from the
captured live datagrams, using the TDR field order as the skeleton.

Observed 'ur' packet (24 bytes), three retransmissions differing only in one
16-bit field:

  75 72 00 10 00 08 00 03 00 00 00 0b 00 00 70 a1 00 00 00 64 00 18 00 00

Prints every plausible framing so the layout can be locked down against the
field names from SUBAGENT_PROTOCOL_SPEC.md.
"""

import struct
import sys

PACKETS = [
    '75720010000800030000000b000070a10000006400180000',
    '75720010000800030000000b000070a20000006400180000',
    '75720010000800030000000b000070a30000006400180000',
]


def main():
    datas = [bytes.fromhex(h) for h in PACKETS]
    base = datas[0]
    print('packet len', len(base))
    print('hex', base.hex(' '))
    print()

    print('=== byte-by-byte (marking bytes that differ across retransmits) ===')
    for i in range(len(base)):
        marks = [d[i] for d in datas]
        diff = 'DIFF' if len(set(marks)) > 1 else '    '
        print('  off=%2d  %02x  %-4s  %3d' % (i, base[i], diff, base[i]))

    print('\n=== u8 fields ===')
    for i in range(len(base)):
        print('  [%2d] = %3d' % (i, base[i]))

    print('\n=== u16 LE fields at even offsets ===')
    for i in range(0, len(base) - 1, 2):
        v = struct.unpack_from('<H', base, i)[0]
        print('  [%2d..%2d] = 0x%04x (%d)' % (i, i + 1, v, v))

    print('\n=== u32 LE fields at 4-byte offsets ===')
    for i in range(0, len(base) - 3, 4):
        v = struct.unpack_from('<I', base, i)[0]
        print('  [%2d..%2d] = 0x%08x (%d)' % (i, i + 3, v, v))

    print('\n=== candidate framing (TDR order: Magic ruHeadLen BodyLen Cmd ProtoVer Seq) ===')
    cands = [
        ('magic=2B + 5 x u16 + u32 + u32 + u32', '<2sHHHHHIII'),
        ('magic=2B + 5 x u16 + u16 seq + u16 + u16 + u16', '<2sHHHHHHHHHH'),
        ('magic=2B + u16 len + u16 body + u16 cmd + u16 ver + u16 seq + 10B payload',
         '<2sHHHHH10s'),
    ]
    for label, fmt in cands:
        size = struct.calcsize(fmt)
        if size == len(base):
            vals = struct.unpack_from(fmt, base, 0)
            print('  OK  %-50s -> %s' % (label, vals))
        else:
            print('  n/a %-50s (size %d != %d)' % (label, size, len(base)))

    print('\n=== interpret with ruHeadLen/BodyLen hypothesis ===')
    w1 = struct.unpack_from('<H', base, 2)[0]
    w2 = struct.unpack_from('<H', base, 4)[0]
    print('  offset2 = 0x%04x ; offset4 = 0x%04x' % (w1, w2))
    print('  len(packet) = %d = 0x%x' % (len(base), len(base)))
    print('  if offset2 == header len  -> %d' % w1)
    print('  if offset4 == body len    -> %d' % w2)
    print('  header(%d) + body(%d) = %d' % (w1, w2, w1 + w2))
    seq16 = struct.unpack_from('<H', base, 12)[0]
    seq16b = struct.unpack_from('<H', base, 14)[0]
    print('  offset12 u16 = 0x%04x ; offset14 u16 = 0x%04x' % (seq16, seq16b))
    print('  retransmit difference is in the low byte of offset12')
    return 0


if __name__ == '__main__':
    sys.exit(main())
