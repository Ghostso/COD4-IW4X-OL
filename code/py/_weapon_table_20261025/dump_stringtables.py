# -*- coding: utf-8 -*-
"""Dump type-37 stringtable assets from an inflated CODOL zone using the
directory run discovered by scan_dir.py."""
import struct, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ZONE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025\code_post_gfx_mp.zone'
DIR_OFF, DIR_COUNT = 0x926, 901
ASSET_BASE = 0x28

d = open(ZONE, 'rb').read()

rows = []
for i in range(DIR_COUNT):
    typ, off, ptr, size = struct.unpack_from('<4I', d, DIR_OFF + i * 16)
    if typ != 37:
        continue
    start = ASSET_BASE + off
    blob = d[start:start + min(size, 200)]
    # name: inline after fixed 16-byte header when ptr == -1
    if ptr == 0xFFFFFFFF:
        nul = blob.find(b'\0', 16)
        name = blob[16:nul].decode('latin-1') if nul > 16 else ''
    else:
        name = '<ptr %#x>' % ptr
    rows.append((i, off, size, name))

print('type37 count', len(rows))
for r in rows:
    print(r[0], hex(r[1]), r[2], r[3])
