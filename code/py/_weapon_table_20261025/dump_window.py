# -*- coding: utf-8 -*-
"""Dump the weapon configstring window (CS_WEAPONS) from an inflated CODOL zone.

Reads every type-37 (stringtable) asset, parses the IW4 stringtable header
{name*, columnCount, rowCount, values*}, and prints rows whose column 0 is a
CS index in the CS_WEAPONS window (>= 5362).
"""
import struct, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ZONE = sys.argv[1] if len(sys.argv) > 1 else r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025\code_post_gfx_mp.zone'
OUT = sys.argv[2] if len(sys.argv) > 2 else None
DIR_OFF, DIR_COUNT = 0x926, 901
ASSET_BASE = 0x28
CS_WEAPONS = 5362
PTR_INLINE = 0xFFFFFFFF

d = open(ZONE, 'rb').read()


def cstr(b, off, limit=512):
    if off < 0 or off >= len(b):
        return None
    e = b.find(b'\0', off, min(len(b), off + limit))
    if e < 0:
        return None
    return b[off:e].decode('latin-1')


def st_hash(s):
    """CODOL_StringTableHash: lower-case, IW4 variant."""
    h = 0
    for ch in s.lower():
        h = (h * 0x1F + ord(ch)) & 0xFFFFFFFF
    return h


results = {}
for i in range(DIR_COUNT):
    typ, off, ptr, size = struct.unpack_from('<4I', d, DIR_OFF + i * 16)
    if typ != 37:
        continue
    start = ASSET_BASE + off
    blob = d[start:start + size]
    name = cstr(blob, 16) if ptr == PTR_INLINE else None
    if name is None or not name.endswith('.csv'):
        continue
    if not name.lower().startswith('mp/constconfigstrings'):
        continue
    cols, rows = struct.unpack_from('<II', blob, 4)
    print('== %s  cols=%d rows=%d size=%d' % (name, cols, rows, size))
    cells = []
    for r in range(rows):
        row = []
        for c in range(cols):
            p = 16 + (r * cols + c) * 8
            if p + 8 > len(blob):
                break
            sptr, h = struct.unpack_from('<II', blob, p)
            if sptr == PTR_INLINE:
                # inline string lives in the same asset stream after the cell array
                row.append(('INLINE@%#x' % p, h))
            else:
                row.append((sptr, h))
        cells.append(row)
    results[name] = (cols, rows, cells)
    for r, row in enumerate(cells[:8]):
        print('   row', r, row)

print('\n-- searching every zone string for hash matches is done separately --')
