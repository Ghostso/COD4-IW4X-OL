# -*- coding: utf-8 -*-
import mem, struct
K = 0x82E13FC
hits = []
for s, sz, data in mem.M.regions:
    pat = struct.pack("<I", K)
    i = data.find(pat)
    while i >= 0:
        hits.append(s + i)
        i = data.find(pat, i+1)
hits.sort()
print("count", len(hits))
# bucket by 0x10000 page
from collections import Counter
c = Counter((h >> 16) << 16 for h in hits)
for k in sorted(c):
    print("%08X : %d" % (k, c[k]))
print()
print("E3-E6 range refs:")
for h in hits:
    if 0xE30000 <= h < 0xE80000:
        print("  %08X" % h)
