# -*- coding: utf-8 -*-
"""Decode one stringtable asset from an inflated CODOL zone (IW4 cell layout)."""
import struct, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ZONE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025\code_post_gfx_mp.zone'
DIR_OFF, DIR_COUNT = 0x926, 901
ASSET_BASE = 0x28
PTR_INLINE = 0xFFFFFFFF
TARGET_INDEX = int(sys.argv[1]) if len(sys.argv) > 1 else 833
MAX_ROWS = int(sys.argv[2]) if len(sys.argv) > 2 else 40

d = open(ZONE, 'rb').read()

typ, off, ptr, size = struct.unpack_from('<4I', d, DIR_OFF + TARGET_INDEX * 16)
start = ASSET_BASE + off
blob = d[start:start + size]
cols, rows = struct.unpack_from('<II', blob, 4)
nameptr, = struct.unpack_from('<I', blob, 0)
name = None
if nameptr == PTR_INLINE:
    e = blob.find(b'\0', 16)
    name = blob[16:e].decode('latin-1')
vals, = struct.unpack_from('<I', blob, 12)
print('asset idx', TARGET_INDEX, 'type', typ, 'name', name, 'cols', cols, 'rows', rows,
      'nameptr', hex(nameptr), 'values_ptr', hex(vals), 'size', size)

cell_base = 16
print('cells span', hex(cell_base), '->', hex(cell_base + cols * rows * 8))
for r in range(min(rows, MAX_ROWS)):
    out = []
    for c in range(cols):
        p = cell_base + (r * cols + c) * 8
        sptr, h = struct.unpack_from('<II', blob, p)
        out.append((hex(sptr), hex(h)))
    print(r, out)
