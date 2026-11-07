# -*- coding: utf-8 -*-
"""Decode a stringtable whose name sits at a known offset inside a zone.

The cell pointers are zone-relative VAs of the form 0x30xxxxxx, so the string
file-offset is (ptr & 0x00FFFFFF) - 0x28 (ASSET_BASE).
"""
import struct, io, sys, csv, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ZONE = sys.argv[1]
NAME = sys.argv[2].encode('latin-1')
OUT = sys.argv[3]
ASSET_BASE = 0x28

d = open(ZONE, 'rb').read()
n = d.find(NAME)
if n < 0:
    raise SystemExit('table name not found')
print('name at', hex(n))

# header is 16 bytes before the name: {nameptr=-1, cols, rows, valsptr}
hdr = n - 16
nameptr, cols, rows, vals = struct.unpack_from('<4I', d, hdr)
print('header @%#x  nameptr=%#x cols=%d rows=%d vals=%#x'
      % (hdr, nameptr, cols, rows, vals))
if cols == 0 or cols > 200 or rows == 0 or rows > 200000:
    raise SystemExit('implausible table shape')

cell0 = n + len(NAME) + 1
print('cells start', hex(cell0), 'end', hex(cell0 + rows * cols * 8))


def read_str(ptr):
    if ptr == 0xFFFFFFFF:
        return None
    off = (ptr & 0x00FFFFFF)
    for base in (0x00, ASSET_BASE):
        o = off - base
        if 0 <= o < len(d):
            e = d.find(b'\0', o, min(len(d), o + 256))
            if e > o:
                try:
                    s = d[o:e].decode('latin-1')
                except Exception:
                    continue
                if s and all(32 <= ord(c) < 127 for c in s):
                    return s
    return '<ptr %08x>' % ptr


table = []
inline_pos = cell0 + rows * cols * 8
for r in range(rows):
    row = []
    for c in range(cols):
        p = cell0 + (r * cols + c) * 8
        if p + 8 > len(d):
            row.append('')
            continue
        sptr, h = struct.unpack_from('<II', d, p)
        if sptr == 0xFFFFFFFF:
            e = d.find(b'\0', inline_pos)
            row.append(d[inline_pos:e].decode('latin-1'))
            inline_pos = e + 1
        else:
            row.append(read_str(sptr))
    table.append(row)

print('\nfirst rows:')
for r in table[:5]:
    print('  ', r)

with open(OUT, 'w', encoding='utf-8-sig', newline='') as fh:
    w = csv.writer(fh)
    w.writerows(table)
print('\nwrote', OUT, rows, 'rows x', cols, 'cols')
