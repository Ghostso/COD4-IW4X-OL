# -*- coding: utf-8 -*-
"""Try every decompressor at every offset of a baseline .bin, and look for
an embedded rawfile table (name pointer + length) inside the const zone."""
import sys, io, zlib, bz2, lzma, os, struct

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

P = sys.argv[1]
d = open(P, 'rb').read()
print('file', os.path.basename(P), len(d), 'bytes')

hits = 0
for off in range(len(d) - 2):
    b0 = d[off]
    if b0 != 0x78:
        continue
    try:
        z = zlib.decompressobj().decompress(d[off:])
    except Exception:
        continue
    if len(z) >= 512:
        print('  zlib @%#x -> %d bytes; head %r' % (off, len(z), z[:40]))
        hits += 1
        if hits > 3:
            break
print('zlib candidates:', hits)

for off in (0, 1, 8, 0x10, 0x20):
    for name, fn in (('zlib', lambda x: zlib.decompress(x)),
                     ('raw-deflate', lambda x: zlib.decompressobj(-15).decompress(x)),
                     ('bz2', bz2.decompress), ('lzma', lzma.decompress)):
        try:
            z = fn(d[off:])
        except Exception:
            continue
        if len(z) > 256:
            print('  %s @%#x -> %d' % (name, off, len(z)))
