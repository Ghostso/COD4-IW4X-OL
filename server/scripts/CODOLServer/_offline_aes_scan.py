#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Offline AES key oracle over a runtime memory image.

For every 4-byte-aligned 16/24/32-byte window, decrypt the first block of the
known 8081 packets and test for the wire magic (ur/us/ru/su).
"""

import argparse
import json
import os
import struct
import time

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def aes_ecb_dec(key, block):
    d = Cipher(algorithms.AES(key), modes.ECB()).decryptor()
    return d.update(block) + d.finalize()


def load_packets(path):
    out = []
    for line in open(path, encoding='utf-8', errors='replace'):
        try:
            o = json.loads(line)
        except ValueError:
            continue
        h = o.get('data_hex')
        if not h:
            continue
        b = bytes.fromhex(h)
        if len(b) >= 20 and (len(b) - 4) % 16 == 0:
            out.append(b)
    return out


def variants(key):
    yield 'raw', key
    # reverse bytes inside each 4-byte dword
    if len(key) % 4 == 0:
        yield 'dwordrev', b''.join(key[i:i + 4][::-1]
                                   for i in range(0, len(key), 4))
    yield 'fullrev', key[::-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('image')
    ap.add_argument('--packets', required=True)
    ap.add_argument('--base-va', type=lambda x: int(x, 0), default=0)
    ap.add_argument('--out', default='')
    args = ap.parse_args()

    data = open(args.image, 'rb').read()
    pkts = load_packets(args.packets)
    print('image=%s len=%d packets=%d lens=%s'
          % (args.image, len(data), len(pkts), [len(p) for p in pkts]))
    if not pkts:
        return 1
    first = pkts[0][:16]

    hits = []
    t0 = time.time()
    n = len(data)
    for size in (16, 24, 32):
        for off in range(0, n - size + 1, 4):
            key = data[off:off + size]
            for vname, k in variants(key):
                try:
                    pt = aes_ecb_dec(k, first)
                except Exception:
                    continue
                if pt[:2] not in (b'ur', b'us', b'ru', b'su'):
                    continue
                # verify all packet first blocks
                ok = 0
                det = []
                for i, p in enumerate(pkts):
                    try:
                        q = aes_ecb_dec(k, p[:16])
                    except Exception:
                        break
                    if q[:2] in (b'ur', b'us', b'ru', b'su'):
                        ok += 1
                        det.append({'pkt': i, 'pt': q.hex()})
                hits.append({'va': args.base_va + off, 'size': size,
                             'variant': vname, 'key': k.hex(),
                             'pt0': pt.hex(), 'confirmed': ok,
                             'details': det})
        print('size=%d done t=%.1fs hits=%d' % (size, time.time() - t0,
                                                len(hits)))

    print('TOTAL HITS', len(hits))
    for h in hits[:40]:
        print(h)
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as fh:
            for h in hits:
                fh.write(json.dumps(h, ensure_ascii=False) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
