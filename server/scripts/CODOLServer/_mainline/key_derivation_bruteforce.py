#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
key_derivation_bruteforce.py -- try plausible session-derived AES keys against
the captured 8081 ciphertexts.

Input: a local_listeners.jsonl from a run that contains both the 8000 TQoS
request/response and 8081 ciphertexts. We derive candidate 16/24/32-byte keys
from the session fields (seq, BusinessID, packet header, response) via raw
slices, XOR, MD5/SHA1/SHA256, endian variants, and AES-ECB test.
"""

import argparse
import hashlib
import json
import os
import struct
import sys

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def aes_ecb_dec(key, block):
    d = Cipher(algorithms.AES(key), modes.ECB()).decryptor()
    return d.update(block) + d.finalize()


def plausible(pt):
    if pt[:2] in (b'ur', b'us', b'ru', b'su'):
        return True
    # header-like: first u16 is a small length and second is plausible
    if len(pt) >= 4:
        a, b = struct.unpack('>HH', pt[:4])
        if a in (16, 24, 0x18) and b < 4096:
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--jsonl', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    rows = [json.loads(l) for l in open(args.jsonl, encoding='utf-8', errors='replace') if l.strip()]
    reqs = [bytes.fromhex(r['data_hex']) for r in rows
            if r.get('proto') == 'udp' and r.get('port') == 8000 and r.get('data_hex')]
    ct = [bytes.fromhex(r['data_hex']) for r in rows
          if r.get('proto') == 'udp' and r.get('port') == 8081 and r.get('data_hex')]
    print('8000 requests', len(reqs), '8081 packets', len(ct))
    if not reqs or not ct:
        print('need both request and ciphertext')
        return 1

    req = reqs[0]
    seq = struct.unpack('>I', req[12:16])[0]
    biz = struct.unpack('>I', req[16:20])[0]
    tail = req[20:24]
    seeds = [req, req[:16], req[8:24], req[12:24], req[16:24], ct[0][:16]]
    # textual seeds seen in the runtime protocol
    for s in (b'CODOL/1.0', b'ru', b'su', b'qos_cs', b'qos_ss',
              b'tencent_ticket', b'QOSCSPkg', b'DW-Ticket-Seed',
              b'356c4bc3', b'43FCB2AC'):
        seeds.append(s)
    seeds += [struct.pack('>I', seq), struct.pack('<I', seq),
              struct.pack('>I', biz), struct.pack('<I', biz),
              tail, struct.pack('>I', 0x18), struct.pack('<I', 0x18)]

    candidates = {}

    def add(name, key):
        if len(key) in (16, 24, 32):
            candidates.setdefault(key, []).append(name)

    for s in seeds:
        add('raw:' + str(len(s)), s[:32])
        add('md5', hashlib.md5(s).digest())
        add('sha1-16', hashlib.sha1(s).digest()[:16])
        add('sha256-16', hashlib.sha256(s).digest()[:16])
        add('sha256-32', hashlib.sha256(s).digest())
        add('sha256-24', hashlib.sha256(s).digest()[:24])
        add('rev', s[::-1][:32])
        add('dwordrev', b''.join(s[i:i+4][::-1] for i in range(0, min(len(s), 32), 4)))

    # pair XORs
    for i in range(len(seeds)):
        for j in range(i + 1, len(seeds)):
            a, b = seeds[i], seeds[j]
            n = min(len(a), len(b), 32)
            add('xor%d_%d' % (i, j), bytes(x ^ y for x, y in zip(a[:n], b[:n])))

    print('candidate keys', len(candidates))
    hits = []
    for key, names in candidates.items():
        try:
            pt = aes_ecb_dec(key, ct[0][:16])
        except Exception:
            continue
        if plausible(pt):
            hits.append({'key': key.hex(), 'names': names,
                         'pt': pt.hex()})
            print('HIT', key.hex(), names, pt.hex())

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, 'w', encoding='utf-8') as fh:
        json.dump(hits, fh, indent=2)
    print('hits', len(hits), 'wrote', args.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
