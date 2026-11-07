# -*- coding: utf-8 -*-
"""Full dump of the stringtable list + row data for a given zone directory."""
import struct, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ZONE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025\code_post_gfx_mp.zone'
DIR_OFF, DIR_COUNT = 0x926, 901
ASSET_BASE = 0x28
PTR_INLINE = 0xFFFFFFFF

d = open(ZONE, 'rb').read()


def cstr(b, off, limit=4096):
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
    hdr_end = 16
    if ptr == PTR_INLINE:
        hdr_end = 16 + len(name) + 1
    cells = []
    ok = True
    for r in range(rows):
        row = []
        for c in range(cols):
            p = hdr_end + (r * cols + c) * 8
            if p + 8 > len(blob):
                ok = False
                break
            sptr, h = struct.unpack_from('<II', blob, p)
            row.append((sptr, h))
        if not ok:
            break
        cells.append(row)
    # string region begins after cells
    str_off = hdr_end + rows * cols * 8
    n_inline = sum(1 for row in cells for sptr, _ in row if sptr == PTR_INLINE)
    print('%-45s cols=%-3d rows=%-6d cells_end=%#x size=%d inline=%d ok=%s'
          % (name, cols, rows, str_off, size, n_inline, ok))
