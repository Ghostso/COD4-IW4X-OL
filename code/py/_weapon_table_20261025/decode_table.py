# -*- coding: utf-8 -*-
"""Decode a stringtable asset from an inflated CODOL zone into CSV.

Layout (measured on code_post_gfx_mp.zone):
  0x00 name pointer (0xFFFFFFFF = inline, string follows the 16-byte header)
  0x04 columnCount
  0x08 rowCount
  0x0C values pointer (0xFFFFFFFF = inline)
  then (columnCount*rowCount) cells of { string pointer, hash }
  then the inline string blob, in cell order (row-major).
"""
import struct, sys, io, csv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ZONE = sys.argv[1]
DIR_OFF = int(sys.argv[2], 0)
DIR_COUNT = int(sys.argv[3], 0)
TARGET = sys.argv[4]
OUT = sys.argv[5]
ASSET_BASE = 0x28
PTR_INLINE = 0xFFFFFFFF

d = open(ZONE, 'rb').read()


def cstr(b, off, limit=8192):
    e = b.find(b'\0', off, min(len(b), off + limit))
    return b[off:e].decode('latin-1') if e > off else None


found = None
for i in range(DIR_COUNT):
    typ, off, ptr, size = struct.unpack_from('<4I', d, DIR_OFF + i * 16)
    if typ != 37:
        continue
    start = ASSET_BASE + off
    blob = d[start:start + size]
    name = cstr(blob, 16) if ptr == PTR_INLINE else None
    if name == TARGET:
        found = blob
        break

if found is None:
    raise SystemExit('stringtable not found: ' + TARGET)

blob = found
cols, rows = struct.unpack_from('<II', blob, 4)
name = cstr(blob, 16)
hdr_end = 16 + len(name) + 1
str_off = hdr_end + rows * cols * 8

# walk the inline string region, assigning strings to inline cells in cell order
strings = {}
p = str_off
for r in range(rows):
    for c in range(cols):
        cellp = hdr_end + (r * cols + c) * 8
        sptr, h = struct.unpack_from('<II', blob, cellp)
        if sptr == PTR_INLINE:
            e = blob.find(b'\0', p)
            if e < 0:
                raise SystemExit('inline string overrun at %#x' % p)
            strings[(r, c)] = blob[p:e].decode('latin-1')
            p = e + 1

print('table', name, 'cols', cols, 'rows', rows, 'strings', len(strings),
      'string region ends', hex(p), 'asset size', len(blob))

with open(OUT, 'w', encoding='utf-8', newline='') as fh:
    w = csv.writer(fh)
    for r in range(rows):
        row = []
        for c in range(cols):
            if (r, c) in strings:
                row.append(strings[(r, c)])
            else:
                sptr, h = struct.unpack_from('<II', blob, hdr_end + (r * cols + c) * 8)
                row.append('<ptr:%08x hash:%08x>' % (sptr, h))
        w.writerow(row)
print('wrote', OUT)
