#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Confirm that confirmed=1 is pure chance (16-bit magic false-positive rate)."""

import json
import os
import random
import sys

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def main():
    pkts = []
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                     'run_codol_001', 'runs', 'SINGLE_V3',
                     'local_listeners.jsonl')
    for line in open(p, encoding='utf-8', errors='replace'):
        o = json.loads(line)
        if 'data_hex' in o:
            pkts.append(bytes.fromhex(o['data_hex']))
    firsts = [x[:16] for x in pkts]

    random.seed(1234)
    n = 20000
    hist = {i: 0 for i in range(10)}
    for _ in range(n):
        k = bytes(random.getrandbits(8) for _ in range(16))
        c = 0
        for f in firsts:
            d = Cipher(algorithms.AES(k), modes.ECB()).decryptor()
            if (d.update(f) + d.finalize())[:2] in (b'ur', b'us', b'ru', b'su'):
                c += 1
        hist[c] += 1
    print('random-key trial histogram (n=%d):' % n)
    for k in sorted(hist):
        if hist[k]:
            print('  confirmed=%d : %d' % (k, hist[k]))
    print('')
    print('=> expected ~4/65536 per key for one packet; a genuine session key')
    print('   would show confirmed=9 (all packets) deterministically.')


if __name__ == '__main__':
    main()
