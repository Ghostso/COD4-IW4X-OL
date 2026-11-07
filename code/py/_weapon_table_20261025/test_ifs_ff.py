# -*- coding: utf-8 -*-
"""Test whether the IWff0100 payload inside a CODOL .ifs decrypts with the same
RSA+AES scheme as a standalone .ff file."""
import struct, sys, io, os, hashlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

DEC = r'D:\BaiduNetdiskDownload\使命召唤OL\_PLAINTEXT_PROJECT\tools'
sys.path.insert(0, DEC)
import codol_ff_decrypt as D

P = sys.argv[1]
d = open(P, 'rb').read()
print('ifs', os.path.basename(P), len(d))

hdr = struct.unpack_from('<I', d, 4)[0]
tail_len = struct.unpack_from('<Q', d, 0x4c)[0]
man_end = d.find(b'IWff0100', hdr)
print('header', hdr, 'manifest end', hex(man_end), 'tail_len', tail_len)

payload = d[man_end:len(d) - tail_len]
print('payload', len(payload), 'bytes; magic', payload[:8])

# Try the standard .ff scheme on the payload
raw = payload
n, dd = D.private_key()
blk = raw[D.RSA_OFF:D.RSA_OFF + D.RSA_LEN]
print('rsa block head', blk[:16].hex())
payload_key = D.rsa_unwrap(n, dd, blk)
print('rsa unwrap ->', None if payload_key is None else len(payload_key))

if payload_key and len(payload_key) == 40:
    key, iv = bytes(payload_key[:24]), bytes(payload_key[24:40])
    print('key', key.hex(), 'iv', iv.hex())
    body = raw[D.BODY_OFF:]
    plain = D.aes_ctr(body[:0x2000], key, iv)
    print('block0 magic', plain[:8])
    print('zone name', plain[300:332].split(b'\0')[0])
else:
    # maybe the payload has its own outer header different from .ff
    print('no PKCS#1 v1.5 unwrap; payload head:')
    for k in range(0, 96, 16):
        row = raw[k:k + 16]
        print('  %04x %-47s %s' % (k, ' '.join('%02x' % b for b in row),
                                   ''.join(chr(b) if 32 <= b < 127 else '.' for b in row)))
