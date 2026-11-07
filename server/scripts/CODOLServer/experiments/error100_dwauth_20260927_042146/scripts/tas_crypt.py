#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tas_crypt.py -- Tenio "TAS" stream cipher (TCLS.dll 0x100D7D60 / 0x100D7720 / 0x100D7920).

Recovered statically from TCLS.dll (VA 0x100D7920 KSA, 0x100D7720 transform,
0x100D7D60 8-byte-key wrapper, 0x100D7BF0 file-time key getter).

Algorithm
---------
KSA(key8) -> (key2[8], sbox[256]):
    key2[i] = key[i] ^ MASK[i],  MASK = 8A E6 9B F3 C1 7D 40 25
    sbox[i] = i
    seed = BE32(key2[0:4]) ^ BE32(key2[4:8])
    state = seed
    for i in 0..255:
        state = (state*0x343FD + 0x269EC3) & 0xFFFFFFFF      # MSVCRT rand()
        j = (state >> 16) & 0xFF
        swap(sbox[i], sbox[j])
    if flag == 0: sbox = inverse(sbox)      # flag==0 -> forward table used by decrypt

transform(key8, flag, buf):
    for i in range(len(buf)):
        x = buf[i]
        if flag:  x ^= i & 0xFF                        # encrypt: index xor first
        x ^= key2[i & 7]
        x  = sbox[x]
        x ^= key2[i & 7]
        if not flag: x ^= i & 0xFF                     # decrypt: index xor last
        buf[i] = x

flag == 1  -> encrypt  (TCLS writes shared memory with flag=1)
flag == 0  -> decrypt  (reader side)

8-byte key sources observed:
  * 0x100D7BF0 GetFileTime(file, last-write) -> pack('<II', dwLowDateTime, dwHighDateTime)
    (used with the launched game exe path in TCLS 0x1003FD10)
  * fallback when the file time is 0: 0x46D14CF9 / 0xEF1DC888
"""

import struct
import sys

MASK = (0x8A, 0xE6, 0x9B, 0xF3, 0xC1, 0x7D, 0x40, 0x25)
DEFAULT_KEY_DWORDS = (0x46D14CF9, 0xEF1DC888)
DEFAULT_KEY = struct.pack('<II', *DEFAULT_KEY_DWORDS)


def ksa(key8, flag):
    """Returns (key2 bytes, table 256-list). flag==0 builds the forward table (decrypt)."""
    if len(key8) < 8:
        key8 = (key8 + b'\x00' * 8)[:8]
    key2 = bytes((key8[i] ^ MASK[i]) & 0xFF for i in range(8))
    sbox = list(range(256))
    seed = ((key2[0] << 24) | (key2[1] << 16) | (key2[2] << 8) | key2[3]) ^ \
           ((key2[4] << 24) | (key2[5] << 16) | (key2[6] << 8) | key2[7])
    state = seed & 0xFFFFFFFF
    for i in range(256):
        state = (state * 0x343FD + 0x269EC3) & 0xFFFFFFFF
        j = (state >> 16) & 0xFF
        sbox[i], sbox[j] = sbox[j], sbox[i]
    if flag == 0:
        inv = [0] * 256
        for i in range(256):
            inv[sbox[i]] = i
        sbox = inv
    return key2, sbox


def transform(key8, flag, buf):
    """In-place transform of a bytes-like buffer. flag==1 encrypt, flag==0 decrypt."""
    key2, table = ksa(key8, flag)
    out = bytearray(buf)
    for i in range(len(out)):
        x = out[i]
        if flag:
            x ^= i & 0xFF
        x ^= key2[i & 7]
        x = table[x]
        x ^= key2[i & 7]
        if not flag:
            x ^= i & 0xFF
        out[i] = x
    return bytes(out)


def encrypt(key8, data):
    return transform(key8, 1, data)


def decrypt(key8, data):
    return transform(key8, 0, data)


def score(data):
    """printable-ASCII / CJK-utf8 friendliness score, higher is better."""
    if not data:
        return 0.0
    printable = sum(1 for b in data if 32 <= b < 127 or b in (9, 10, 13))
    return printable / float(len(data))


def _selftest():
    import os
    key = DEFAULT_KEY
    for flag_name, fn in (('enc', encrypt), ('dec', decrypt)):
        pass
    plain = bytes(range(256)) * 3 + b'[client]\nname=codoMP_client_shipRetail.exe\n'
    ct = encrypt(key, plain)
    rt = decrypt(key, ct)
    assert rt == plain, 'round-trip failed'
    print('selftest OK  (enc!=plain: %s)' % (ct != plain))
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return _selftest()

    mode = sys.argv[1]
    if mode == 'selftest':
        return _selftest()
    if mode == 'dec' or mode == 'enc':
        keyhex = sys.argv[2]
        key = bytes.fromhex(keyhex) if keyhex != 'default' else DEFAULT_KEY
        path = sys.argv[3]
        data = open(path, 'rb').read()
        out = decrypt(key, data) if mode == 'dec' else encrypt(key, data)
        dst = path + '.' + ('dec' if mode == 'dec' else 'enc')
        with open(dst, 'wb') as f:
            f.write(out)
        print('key=%s  in=%d bytes  score=%.3f  -> %s' % (key.hex(), len(data), score(out), dst))
        print(repr(out[:160]))
        return 0
    if mode == 'brute':
        # brute known key candidates against a file
        import os
        path = sys.argv[2]
        data = open(path, 'rb').read()
        cands = {
            'default-ft': DEFAULT_KEY,
            '1111x8': b'11111111',
            '1111x16': b'1111111111111111',
            'configcfg': b'configconfigconf',
        }
        # file-time keys of nearby executables / dlls
        base = os.path.dirname(os.path.abspath(path))
        roots = [base, os.path.dirname(base), os.path.dirname(os.path.dirname(base))]
        files = []
        for r in roots:
            for pat in ('*.exe', '*.dll'):
                try:
                    for n in os.listdir(r):
                        if n.lower().endswith(('.exe', '.dll')):
                            files.append(os.path.join(r, n))
                except OSError:
                    pass
        for p in files:
            try:
                st = os.stat(p)
                ft = st.st_mtime
            except OSError:
                continue
        results = []
        for name, key in cands.items():
            for flag, fn in ((0, decrypt), (1, encrypt)):
                out = fn(key, data)
                results.append((score(out), name, flag, out))
        results.sort(key=lambda r: -r[0])
        for sc, name, flag, out in results[:6]:
            print('%.3f  %-10s flag=%d  %r' % (sc, name, flag, out[:64]))
        return 0
    print(__doc__)
    return 1


if __name__ == '__main__':
    sys.exit(main())
