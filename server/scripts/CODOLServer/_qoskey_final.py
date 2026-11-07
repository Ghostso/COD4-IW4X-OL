#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Final consistency checks for the 8081 key-source report."""

import json
import os
import struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKT = os.path.join(ROOT, 'run_codol_001', 'runs', 'SINGLE_V3',
                   'local_listeners.jsonl')


def main():
    pkts = []
    for line in open(PKT, encoding='utf-8', errors='replace'):
        o = json.loads(line)
        if 'data_hex' in o:
            pkts.append(bytes.fromhex(o['data_hex']))

    print('=== 8081: block count, tail split ===')
    for i, p in enumerate(pkts):
        body = p[:-4]
        n = len(body) // 16
        print('#%d len=%3d blocks=%2d tail4=%s  body_head=%s'
              % (i, len(p), n, p[-4:].hex(), body[:8].hex()))

    # Is the 4-byte tail perhaps the plaintext of a 5th? no: it is not a
    # multiple of 16, so it is a plaintext trailer (unencrypted).
    print('')
    print('tail4 as u32be:', [struct.unpack('>I', p[-4:])[0] for p in pkts])
    print('tail4 as u16be pair:',
          [(struct.unpack('>H', p[-4:-2])[0], struct.unpack('>H', p[-2:])[0])
           for p in pkts])

    # packet #6 duplicate block positions
    p6 = pkts[6][:-4]
    blk = p6[29 * 16:30 * 16]
    print('')
    print('#6 duplicate block =', blk.hex())
    print('  occurrences at byte offsets',
          [29 * 16, 37 * 16], '->', 29 * 16, 37 * 16)
    print('#6 body len =', len(p6), 'offset delta =', (37 - 29) * 16)

    # 8000 frame for cross-reference
    f = os.path.join(ROOT, 'run_codol_001', 'runs', 'SINGLE_V0B',
                     'local_listeners.jsonl')
    if os.path.exists(f):
        print('')
        print('=== 8000/UDP reference frames ===')
        for line in open(f, encoding='utf-8', errors='replace'):
            o = json.loads(line)
            for k in ('data_hex', 'sent_reply'):
                if k in o and o[k]:
                    b = b''
                    if isinstance(o[k], str):
                        try:
                            b = bytes.fromhex(o[k])
                        except ValueError:
                            continue
                    print('port=%s peer=%s %s=%s'
                          % (o.get('port'), o.get('peer'), k, b.hex()))


if __name__ == '__main__':
    main()
