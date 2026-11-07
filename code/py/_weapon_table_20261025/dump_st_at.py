# -*- coding: utf-8 -*-
"""Dump stringtables given an explicit directory offset/count."""
import struct, sys, io, csv, re, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ZONE, DIR_OFF, DIR_COUNT, OUTDIR = sys.argv[1], int(sys.argv[2], 0), int(sys.argv[3], 0), sys.argv[4]
ASSET_BASE = 0x28
PTR_INLINE = 0xFFFFFFFF

d = open(ZONE, 'rb').read()


def cstr(b, off, limit=8192):
    e = b.find(b'\0', off, min(len(b), off + limit))
    return b[off:e].decode('latin-1') if e > off else None


def h31(s):
    h = 0
    for ch in s:
        h = (h * 31 + ch) & 0xFFFFFFFF
    return h


index = {}
for m in re.finditer(rb'[ -~]{1,400}\x00', d):
    s = m.group()[:-1]
    index.setdefault(h31(s), s.decode('latin-1'))

os.makedirs(OUTDIR, exist_ok=True)
written = 0
for i in range(DIR_COUNT):
    typ, off, ptr, size = struct.unpack_from('<4I', d, DIR_OFF + i * 16)
    if typ != 37:
        continue
    blob = d[ASSET_BASE + off: ASSET_BASE + off + size]
    name = cstr(blob, 16) if ptr == PTR_INLINE else None
    if not name or not name.endswith('.csv'):
        continue
    cols, rows = struct.unpack_from('<II', blob, 4)
    hdr_end = 16 + len(name) + 1
    if hdr_end + rows * cols * 8 > len(blob):
        print('skip', name)
        continue
    strings = {}
    p = hdr_end + rows * cols * 8
    for r in range(rows):
        for c in range(cols):
            sptr, h = struct.unpack_from('<II', blob, hdr_end + (r * cols + c) * 8)
            if sptr == PTR_INLINE:
                e = blob.find(b'\0', p)
                strings[(r, c)] = blob[p:e].decode('latin-1')
                p = e + 1
    out = os.path.join(OUTDIR, name.replace('/', '_'))
    with open(out, 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh)
        for r in range(rows):
            row = []
            for c in range(cols):
                if (r, c) in strings:
                    row.append(strings[(r, c)])
                else:
                    sptr, h = struct.unpack_from('<II', blob, hdr_end + (r * cols + c) * 8)
                    row.append(index.get(h, '<unresolved %08x>' % h))
            w.writerow(row)
    written += 1
    print('%-45s cols=%d rows=%d' % (name, cols, rows))
print('wrote', written)
