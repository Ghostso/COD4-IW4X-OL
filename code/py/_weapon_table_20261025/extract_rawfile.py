# -*- coding: utf-8 -*-
"""Find and extract the coMarketplaceItems rawfile (type 36) from a zone."""
import struct, io, sys, os, zlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ZONE = sys.argv[1]
WANT = sys.argv[2].encode('latin-1')
OUT = sys.argv[3]
ASSET_BASE = 0x28

d = open(ZONE, 'rb').read()
N = len(d)
print('zone', os.path.basename(ZONE), len(d), 'looking for', WANT)


def plausible(o):
    if o + 16 > N:
        return False
    t, off, ptr, sz = struct.unpack_from('<4I', d, o)
    return (t < 64 and off < N and sz < N and off + sz <= N and ptr in (0, 0xFFFFFFFF))


runs = []
o = 0
while o + 16 <= N:
    if plausible(o):
        s, k = o, 0
        while o + 16 <= N and plausible(o):
            k += 1
            o += 16
        if k >= 20:
            runs.append((s, k))
    else:
        o += 1
runs.sort(key=lambda x: -x[1])
dir_off, count = runs[0]
print('directory %#x count %d' % (dir_off, count))

found = 0
for i in range(count):
    t, off, ptr, sz = struct.unpack_from('<4I', d, dir_off + i * 16)
    if t not in (36, 37):
        continue
    blob = d[ASSET_BASE + off: ASSET_BASE + off + min(sz, 200)]
    nm = None
    if ptr == 0xFFFFFFFF:
        e = blob.find(b'\0', 16)
        if e > 16:
            nm = blob[16:e]
    if nm and WANT.lower() in nm.lower():
        print('found: entry %d type=%d off=%#x size=%d name=%r'
              % (i, t, off, sz, nm.decode('latin-1')))
        raw = d[ASSET_BASE + off: ASSET_BASE + off + sz]
        found += 1
        # rawfile payload may be zlib; try
        payload = raw
        hdr_end = 16 + len(nm) + 1
        body = raw[hdr_end:]
        for cand, tag in ((body, 'after-name'), (raw, 'whole')):
            try:
                z = zlib.decompress(cand)
                if len(z) > 64:
                    payload = z
                    print('   zlib (%s) -> %d bytes' % (tag, len(z)))
                    break
            except Exception:
                pass
        open(OUT, 'wb').write(payload)
        print('   wrote', OUT, len(payload), 'bytes')

print('matches:', found)
