#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test AES key hypotheses against the 8081 ciphertexts.

Oracle: decrypted first block should start with the QoS magic 'ru' (0x7275)
or 'su' (0x7375), or be a small big-endian length/structure.
"""

import hashlib
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKT = os.path.join(ROOT, 'run_codol_001', 'runs', 'SINGLE_V3',
                   'local_listeners.jsonl')

try:
    from Crypto.Cipher import AES
    HAVE_PYCRYPTODOME = True
except Exception:
    HAVE_PYCRYPTODOME = False

try:
    from cryptography.hazmat.primitives.ciphers import (
        Cipher, algorithms, modes)
    HAVE_CRYPTOGRAPHY = True
except Exception:
    HAVE_CRYPTOGRAPHY = False


def load():
    out = []
    for line in open(PKT, encoding='utf-8', errors='replace'):
        o = json.loads(line)
        if 'data_hex' in o:
            out.append(bytes.fromhex(o['data_hex']))
    return out


def key_candidates():
    ks = []
    base = [b'', b'codol', b'CODOL', b'qos', b'QOS', b'tencent', b'Tencent',
            b'tqos', b'QOSCSPkg', b'qos_cs', b'qos_ss', b'356c4bc3',
            b'356C4BC3', b'DW-Ticket-Seed', b'config_mp.cfg', b'TCLS']
    for b in base:
        for n in (16, 24, 32):
            if 0 < len(b) <= n:
                ks.append(('pad0:' + b.decode('latin1', 'replace'),
                           (b + bytes(n))[:n]))
                ks.append(('rep:' + b.decode('latin1', 'replace'),
                           (b * (n // len(b) + 1))[:n]))
        ks.append(('md5:' + b.decode('latin1', 'replace'),
                   hashlib.md5(b).digest() if b else hashlib.md5(b'').digest()))
        ks.append(('sha256:' + b.decode('latin1', 'replace'),
                   hashlib.sha256(b).digest()))
    # numeric -> bytes
    for v in (0x356C4BC3, 0x356c4bc3, 0x1109, 0x1120, 0x1121):
        for end in ('little', 'big'):
            b = v.to_bytes(4, end)
            ks.append(('dw%08x-%s' % (v, end), (b * 8)[:32]))
            ks.append(('dw%08x-%s-md5' % (v, end), hashlib.md5(b).digest()))
    # the 43FC... hex string from the dump
    hx = (b'43FCB2ACF2D72593DD7CD1C69E0F03C0'
          b'7229F4C83166F7B05BA0C5FE3AA3A2D93EK2')
    try:
        raw = bytes.fromhex(hx[:64].decode())
        ks.append(('43FC-raw', raw[:32]))
        ks.append(('43FC-md5', hashlib.md5(raw).digest()))
    except ValueError:
        pass
    # dedupe
    seen = set()
    out = []
    for name, k in ks:
        if len(k) in (16, 24, 32) and k not in seen:
            seen.add(k)
            out.append((name, k))
    return out


def aes_ecb_dec(key, data):
    if HAVE_PYCRYPTODOME:
        return AES.new(key, AES.MODE_ECB).decrypt(data)
    c = Cipher(algorithms.AES(key), modes.ECB())
    d = c.decryptor()
    return d.update(data) + d.finalize()


def aes_cbc_dec(key, iv, data):
    if HAVE_PYCRYPTODOME:
        return AES.new(key, AES.MODE_CBC, iv).decrypt(data)
    c = Cipher(algorithms.AES(key), modes.CBC(iv))
    d = c.decryptor()
    return d.update(data) + d.finalize()


def interesting(pt):
    return (pt[:2] in (b'ru', b'su') or pt[:2] in (b'\x00\x10', b'\x00\x18',
                                                   b'\x00\x20', b'\x00\x08') or
            pt[:4] == b'QOSC' or b'qos' in pt[:16].lower())


def main():
    print('pycryptodome=%s cryptography=%s'
          % (HAVE_PYCRYPTODOME, HAVE_CRYPTOGRAPHY))
    if not (HAVE_PYCRYPTODOME or HAVE_CRYPTOGRAPHY):
        print('no AES backend available')
        return 1
    pkts = load()
    ks = key_candidates()
    print('packets=%d keys=%d' % (len(pkts), len(ks)))
    found = []
    for name, k in ks:
        for i, p in enumerate(pkts):
            body = p[:-4]
            body = body[:len(body) - (len(body) % 16)]
            if not body:
                continue
            try:
                pt = aes_ecb_dec(k, body[:16])
            except Exception:
                continue
            if interesting(pt):
                found.append(('ECB', name, k.hex(), i, pt.hex(), p[:16].hex()))
            for ivname, iv in (('zero', bytes(16)),
                               ('ctr', None)):
                if iv is None:
                    continue
                try:
                    pt2 = aes_cbc_dec(k, iv, body[:16])
                except Exception:
                    continue
                if interesting(pt2):
                    found.append(('CBC/' + ivname, name, k.hex(), i,
                                  pt2.hex(), p[:16].hex()))
    print('')
    if not found:
        print('NO AES key from the candidate set produces a plausible header')
    for f in found[:40]:
        print(f)


if __name__ == '__main__':
    sys.exit(main() or 0)
