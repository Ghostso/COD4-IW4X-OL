# -*- coding: utf-8 -*-
"""Dump every stringtable's dimensions and first rows from an inflated CODOL zone."""
import struct, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ZONE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025\code_post_gfx_mp.zone'
DIR_OFF, DIR_COUNT = 0x926, 901
ASSET_BASE = 0x28
PTR_INLINE = 0xFFFFFFFF

d = open(ZONE, 'rb').read()


def cstr(b, off, limit=512):
    e = b.find(b'\0', off, min(len(b), off + limit))
    return b[off:e].decode('latin-1') if e > off else None


for i in range(DIR_COUNT):
    typ, off, ptr, size = struct.unpack_from('<4I', d, DIR_OFF + i * 16)
    if typ != 37:
        continue
    start = ASSET_BASE + off
    blob = d[start:start + size]
    name = cstr(blob, 16) if ptr == PTR_INLINE else None
    cols, rows = struct.unpack_from('<II', blob, 4)
    print('%4d %-45s cols=%-4d rows=%-6d size=%d' % (i, name, cols, rows, size))
