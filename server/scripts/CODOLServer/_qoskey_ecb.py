#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe the 16-byte-block hypothesis for the 8081 channel.

Facts under test:
  * every packet length - 4 is a multiple of 16
  * packet #6 contains an exact repeated 16-byte block
  * under ECB, identical 16-byte plaintext blocks make identical ciphertext
    blocks anywhere in the stream
"""

import json
import os
import struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE_BASE = 0x00994000
DUMP = os.path.join(ROOT, 'run_codol_001', 'runs',
                    'ENGINE_DUMP_20260925_114204', 'engine', 'engine_best.bin')
PKT = os.path.join(ROOT, 'run_codol_001', 'runs', 'SINGLE_V3',
                   'local_listeners.jsonl')

AES_SBOX = bytes.fromhex(
    '637c777bf26b6fc53001672bfed7ab76'
    'ca82c97dfa5947f0add4a2af9ca472c0'
    'b7fd9326363ff7cc34a5e5f171d83115'
    '04c723c31896059a071280e2eb27b275'
    '09832c1a1b6e5aa0523bd6b329e32f84'
    '53d100ed20fcb15b6acbbe394a4c58cf'
    'd0efaafb434d338545f9027f503c9fa8'
    '51a3408f929d38f5bcb6da2110fff3d2'
    'cd0c13ec5f974417c4a77e3d645d1973'
    '60814fdc222a908846eeb814de5e0bdb'
    'e0323a0a4906245cc2d3ac629195e479'
    'e7c8376d8dd54ea96c56f4ea657aae08'
    'ba78252e1ca6b4c6e8dd741f4bb8a9'
    '8a703eb5664803f60e613557b986c11d'
    '9e1f8e2ffb414040d9d43a5f05b1a3'
    'ff0f82b5b4ded1e7a1e524d3b0d67a')

AES_INV_SBOX = bytes.fromhex(
    '52096ad53036a538bf40a39e81f3d7fb'
    '7ce339829b2fff87348e4344c4dee9cb'
    '547b9432a6c2233dee4c950b42fac34e'
    '082ea16628d924b2765ba2496d8bd125'
    '72f8f66486689816d4a45ccc5d65b692'
    '6c704850fdedb9da5e154657a78d9d84'
    '90d8ab008cbcd30af7e45805b8b34506'
    'd02c1e8fca3f0f02c1afbd0301138a6b'
    '3a9111414f67dcea97f2cfcef0b4e673'
    '96ac7422e7ad3585e2f937e81c75df6e'
    '47f11a711d29c5896fb7620eaa18be1b'
    'fc563e4bc6d279209adbc0fe78cd5af4'
    '1fdda8338807c731b11210592780ec5f'
    '60517fa919b54a0d2de57a9f93c99cef'
    'a0e03b4dae2af5b0c8ebbb3c83539961'
    '172b047eba77d626e169146355210c7d')


def blocks(b):
    return [b[i:i + 16] for i in range(0, len(b), 16)]


def main():
    pkts = []
    for line in open(PKT, encoding='utf-8', errors='replace'):
        o = json.loads(line)
        if 'data_hex' in o:
            pkts.append(bytes.fromhex(o['data_hex']))

    print('=== length / alignment ===')
    for i, b in enumerate(pkts):
        print('#%d len=%3d len-4=%3d %%16=%d  footer=%s'
              % (i, len(b), len(b) - 4, (len(b) - 4) % 16, b[-4:].hex()))

    print('')
    print('=== repeated 16-byte blocks (ECB signature) ===')
    all_blocks = {}
    for i, b in enumerate(pkts):
        body = b[:-4]
        seen = {}
        for n, blk in enumerate(blocks(body)):
            if blk in seen:
                print('#%d block %d == block %d  %s'
                      % (i, seen[blk], n, blk.hex()))
            seen[blk] = n
            all_blocks.setdefault(blk, []).append((i, n))
    print('')
    print('cross-packet duplicate ciphertext blocks:')
    for blk, locs in all_blocks.items():
        if len(locs) > 1:
            print('  %s -> %s' % (blk.hex(), locs))

    print('')
    print('=== crypto artifacts in runtime .tls window ===')
    d = open(DUMP, 'rb').read()
    for pat in (AES_SBOX, AES_INV_SBOX,
                b'AES', b'aes', b'Rijndael', b'RC4', b'ChaCha',
                b'HMAC', b'SHA256', b'Crypt', b'EVP_',
                b'CBC', b'ECB', b'CTR', b'PKCS7', b'QOS_CS_MAGIC'):
        offs = []
        s = 0
        while len(offs) < 6:
            i = d.find(pat, s)
            if i < 0:
                break
            offs.append(i)
            s = i + 1
        if offs:
            print('  %-20s %s' % (
                repr(pat[:20]),
                ', '.join('0x%08X' % (ENGINE_BASE + o) for o in offs)))

    # Where are the QoS tables relative to the .tls start?
    print('')
    print('tls_va_start=0x00B0A000  window_start=0x00994000  '
          'qos_cs=0x00E444EC  qos_ss=0x00E4042C')


if __name__ == '__main__':
    main()
