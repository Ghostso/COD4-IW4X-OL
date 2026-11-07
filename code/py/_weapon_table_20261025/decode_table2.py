# -*- coding: utf-8 -*-
"""Resolve de-duplicated (non-inline) stringtable cells by hash.

The inline-string region is walked in cell order, so the boundary between
inline strings and the shared blob is known. Every non-inline cell's hash is
then matched against the hash of every NUL-terminated string in the zone.
"""
import struct, sys, io, csv, re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ZONE = sys.argv[1]
DIR_OFF = int(sys.argv[2], 0)
DIR_COUNT = int(sys.argv[3], 0)
TARGET = sys.argv[4]
OUT = sys.argv[5]
ASSET_BASE = 0x28
PTR_INLINE = 0xFFFFFFFF

d = open(ZONE, 'rb').read()


def h31(s):
    h = 0
    for ch in s:
        h = (h * 31 + ch) & 0xFFFFFFFF
    return h


def cstr(b, off, limit=8192):
    e = b.find(b'\0', off, min(len(b), off + limit))
    return b[off:e].decode('latin-1') if e > off else None


blob = None
for i in range(DIR_COUNT):
    typ, off, ptr, size = struct.unpack_from('<4I', d, DIR_OFF + i * 16)
    if typ != 37:
        continue
    start = ASSET_BASE + off
    b = d[start:start + size]
    if (cstr(b, 16) if ptr == PTR_INLINE else None) == TARGET:
        blob = b
        break
if blob is None:
    raise SystemExit('not found')

cols, rows = struct.unpack_from('<II', blob, 4)
name = cstr(blob, 16)
hdr_end = 16 + len(name) + 1
str_off = hdr_end + rows * cols * 8

strings = {}
p = str_off
for r in range(rows):
    for c in range(cols):
        sptr, h = struct.unpack_from('<II', blob, hdr_end + (r * cols + c) * 8)
        if sptr == PTR_INLINE:
            e = blob.find(b'\0', p)
            strings[(r, c)] = blob[p:e].decode('latin-1')
            p = e + 1

# Build hash index over every NUL-terminated string in the whole zone.
index = {}
for m in re.finditer(rb'[ -~]{1,300}\x00', d):
    s = m.group()[:-1]
    index.setdefault(h31(s), s.decode('latin-1'))

unresolved = 0
rows_out = []
for r in range(rows):
    row = []
    for c in range(cols):
        if (r, c) in strings:
            row.append(strings[(r, c)])
        else:
            sptr, h = struct.unpack_from('<II', blob, hdr_end + (r * cols + c) * 8)
            v = index.get(h)
            if v is None:
                unresolved += 1
                v = '<unresolved %08x>' % h
            row.append(v)
    rows_out.append(row)

print('table', name, 'cols', cols, 'rows', rows, 'inline', len(strings),
      'unresolved', unresolved)

with open(OUT, 'w', encoding='utf-8', newline='') as fh:
    csv.writer(fh).writerows(rows_out)
print('wrote', OUT)
