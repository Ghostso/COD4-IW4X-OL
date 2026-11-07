# -*- coding: utf-8 -*-
"""Dump every stringtable from an inflated zone, trying each candidate
directory run discovered by scan_dir.py."""
import struct, sys, io, csv, re, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ZONE = sys.argv[1]
OUTDIR = sys.argv[2]
ASSET_BASE = 0x28
PTR_INLINE = 0xFFFFFFFF

d = open(ZONE, 'rb').read()
N = len(d)


def plausible(o):
    if o + 16 > N:
        return False
    t, off, ptr, sz = struct.unpack_from('<4I', d, o)
    return (t < 64 and off < N and sz < N and off + sz <= N and ptr in (0, PTR_INLINE))


runs = []
o = 0
while o + 16 <= N:
    if plausible(o):
        s = o
        n = 0
        while o + 16 <= N and plausible(o):
            n += 1
            o += 16
        if n >= 50:
            runs.append((s, n))
    else:
        o += 1
runs.sort(key=lambda x: -x[1])
print('candidate directory runs:', [(hex(s), n) for s, n in runs[:6]])


def cstr(b, off, limit=8192):
    e = b.find(b'\0', off, min(len(b), off + limit))
    return b[off:e].decode('latin-1') if e > off else None


def h31(s):
    h = 0
    for ch in s:
        h = (h * 31 + ch) & 0xFFFFFFFF
    return h


index = {}
for m in re.finditer(rb'[ -~]{1,400}\x00', d):
    s = m.group()[:-1]
    index.setdefault(h31(s), s.decode('latin-1'))

os.makedirs(OUTDIR, exist_ok=True)
seen = set()
for dir_off, count in runs[:3]:
    for i in range(count):
        typ, off, ptr, size = struct.unpack_from('<4I', d, dir_off + i * 16)
        if typ != 37:
            continue
        blob = d[ASSET_BASE + off: ASSET_BASE + off + size]
        name = cstr(blob, 16) if ptr == PTR_INLINE else None
        if not name or not name.endswith('.csv') or name in seen:
            continue
        cols, rows = struct.unpack_from('<II', blob, 4)
        hdr_end = 16 + len(name) + 1
        if hdr_end + rows * cols * 8 > len(blob):
            print('skip (oversize)', name)
            continue
        seen.add(name)
        strings = {}
        p = hdr_end + rows * cols * 8
        for r in range(rows):
            for c in range(cols):
                sptr, h = struct.unpack_from('<II', blob, hdr_end + (r * cols + c) * 8)
                if sptr == PTR_INLINE:
                    e = blob.find(b'\0', p)
                    strings[(r, c)] = blob[p:e].decode('latin-1')
                    p = e + 1
        out = os.path.join(OUTDIR, name.replace('/', '_'))
        with open(out, 'w', encoding='utf-8', newline='') as fh:
            w = csv.writer(fh)
            for r in range(rows):
                row = []
                for c in range(cols):
                    if (r, c) in strings:
                        row.append(strings[(r, c)])
                    else:
                        sptr, h = struct.unpack_from('<II', blob, hdr_end + (r * cols + c) * 8)
                        row.append(index.get(h, '<unresolved %08x>' % h))
                w.writerow(row)
        print('%-50s cols=%-3d rows=%d' % (name, cols, rows))
print('total tables written:', len(seen))
