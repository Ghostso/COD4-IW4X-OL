# -*- coding: utf-8 -*-
"""Deep unpack of a CODOL .ff zone: report every section/block, and whether the
per-block SHA-256 verification succeeds. Dumps the raw concatenated stream so
we can inspect what the zlib stage actually receives."""
import sys, io, hashlib, zlib, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

FF = sys.argv[1]
OUTDIR = sys.argv[2]
LASTIV = len(sys.argv) > 3 and sys.argv[3] == 'last'

DEC = r'D:\BaiduNetdiskDownload\使命召唤OL\_PLAINTEXT_PROJECT\tools'
sys.path.insert(0, DEC)
import codol_ff_decrypt as D

BLOCK = 0x2000
OUTER = 0x115
L1_OFF = 336
DATA_BLOCKS_PER_SECTION = 256

raw = open(FF, 'rb').read()
key, iv = D.recover_key(raw)
body = raw[OUTER:]
print('ff bytes', len(raw), 'body', len(body), 'iv', iv.hex())


def block_at(p):
    b = body[p:p + BLOCK]
    return b + b"\0" * (BLOCK - len(b))


block0 = D.aes_ctr(block_at(0), key, iv)
print('magic', block0[:8], 'zone', block0[300:332].split(b'\0')[0])

out = bytearray()
pos, sec, stats = BLOCK, 0, []
while pos < len(body):
    d1 = block0[L1_OFF + sec * 32: L1_OFF + sec * 32 + 32]
    if d1 == b'\0' * 32:
        print('section %d: empty L1 entry -> stop' % sec)
        break
    enc = block_at(pos)
    pos += BLOCK
    l2 = D.aes_ctr(enc, key, d1[:16])
    n = ok = 0
    while pos < len(body) and n < DATA_BLOCKS_PER_SECTION:
        d2 = l2[n * 32:(n + 1) * 32]
        if d2 == b'\0' * 32:
            break
        e = block_at(pos)
        pos += BLOCK
        b = D.aes_ctr(e, key, d2[:16])
        if hashlib.sha256(b).digest() != d2:
            print('section %d block %d: SHA mismatch' % (sec, n))
            break
        out.extend(b)
        ok += 1
        n += 1
    stats.append(ok)
    print('section %d: %d blocks verified' % (sec, ok))
    sec += 1
    if ok == 0:
        break

os.makedirs(OUTDIR, exist_ok=True)
name = os.path.basename(FF).replace('.ff', '.stream.bin')
ostr = os.path.join(OUTDIR, name)
open(ostr, 'wb').write(bytes(out))
print('concatenated stream', len(out), '->', ostr)
print('  head', bytes(out[:32]).hex())
try:
    z = zlib.decompress(bytes(out))
    print('  zlib OK ->', len(z), 'bytes')
    open(ostr.replace('.stream.bin', '.zone.bin'), 'wb').write(z)
except Exception as e:
    print('  zlib failed:', e)
