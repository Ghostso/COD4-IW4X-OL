# -*- coding: utf-8 -*-
"""Locate the XAsset directory in an inflated CODOL zone, using a known
stringtable asset offset as an anchor."""
import struct, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ZONE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025\code_post_gfx_mp.zone'
ANCHOR_NAME = b'mp/coweaponattachmenttable.csv'

d = open(ZONE, 'rb').read()
n = len(d)
print('zone bytes', n)

anchor = d.find(ANCHOR_NAME)
print('anchor string at', hex(anchor))

# The stringtable asset starts at its name pointer slot; for these zones the
# name is inline at asset_start + 16 (ptr=-1) per the observed layout.
# Try every plausible asset start = anchor - 16 and see if a directory entry
# of the form (type=37, offset, ptr, size) with offset+ASSET_BASE == start exists.
ASSET_BASE = 0x28
cands = []
for start in range(anchor - 64, anchor + 1):
    off = start - ASSET_BASE
    if off < 0:
        continue
    pat = struct.pack('<I', off)
    i = 0
    while True:
        i = d.find(pat, i)
        if i < 0:
            break
        if i % 4 == 0 and i + 16 <= n:
            typ, o, ptr, size = struct.unpack_from('<4I', d, i)
            if typ == 37 and o == off:
                cands.append((i, start, size))
        i += 1
print('candidates (dir_entry_off, asset_start, size):')
for c in cands[:20]:
    print('  dir@%#x start=%#x size=%d' % (c[0], c[1], c[2]))
