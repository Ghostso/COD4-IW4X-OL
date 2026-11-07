# -*- coding: utf-8 -*-
"""Extract the bl_pc_* constbaseline rawfiles from a *_const.ff zone and
decompress them (they are the retail gamestate baselines)."""
import struct, re, zlib, io, sys, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ZONE = sys.argv[1]
OUT = sys.argv[2]
NAME_RE = re.compile(rb'mp/constbaselines/(bl_pc_[a-z0-9_]+\.bin)')

d = open(ZONE, 'rb').read()
os.makedirs(OUT, exist_ok=True)
print('zone bytes', len(d))

seen = set()
for m in NAME_RE.finditer(d):
    name = m.group(1).decode()
    if name in seen:
        continue
    seen.add(name)
    # the rawfile cell holds {name ptr=inline, hash, data ptr, len}; the payload
    # usually follows the name string, so search for a zlib header nearby first
    start = m.end() + 1
    found = None
    for probe in range(start, min(len(d), start + 4096)):
        if d[probe] == 0x78 and d[probe + 1] in (0x01, 0x9C, 0xDA):
            try:
                data = zlib.decompressobj().decompress(d[probe:])
                if len(data) > 256:
                    found = (probe, data)
                    break
            except Exception:
                pass
    if found is None:
        print('%-46s NO zlib payload found near %#x' % (name, start))
        continue
    probe, data = found
    path = os.path.join(OUT, name)
    open(path, 'wb').write(data)
    print('%-46s zlib@%#x  %d -> %d bytes' % (name, probe, len(d) - probe, len(data)))

print('extracted', len(seen))
