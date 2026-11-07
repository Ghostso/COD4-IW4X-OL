# -*- coding: utf-8 -*-
"""List every weapon-name string in a client memory dump with its VA and the
surrounding bytes, to reconstruct the client's loaded-weapon name block."""
import re, struct, sys, io, mmap

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

MEM = sys.argv[1]
IMAGE_BASE = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x400000

f = open(MEM, 'rb')
m = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
N = len(m)
print('dump', N, 'base', hex(IMAGE_BASE))

hits = []
for mt in re.finditer(rb'(?<![\x20-\x7e])([a-z0-9_]{2,44}_mp)\x00', m):
    hits.append((mt.start(), mt.group(1).decode('latin-1')))

print('weapon-like strings:', len(hits))
prev_end = -1
for off, s in hits:
    gap = off - prev_end if prev_end >= 0 else 0
    print('  %#010x va=%#010x gap=%-5d %s' % (off, IMAGE_BASE + off, gap, s))
    prev_end = off + len(s) + 1

# cluster boundaries: a gap > 0x400 starts a new block
blocks = []
cur = [hits[0]] if hits else []
for a, b in zip(hits, hits[1:]):
    if b[0] - (a[0] + len(a[1]) + 1) > 0x400:
        blocks.append(cur)
        cur = []
    cur.append(b)
if cur:
    blocks.append(cur)
print('\nblocks:', len(blocks))
for i, blk in enumerate(blocks):
    print('  block %d  %#x..%#x  %d names: %s'
          % (i, blk[0][0], blk[-1][0], len(blk), [x[1] for x in blk][:6]))
