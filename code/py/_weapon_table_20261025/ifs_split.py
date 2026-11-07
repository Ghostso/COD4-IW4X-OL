# -*- coding: utf-8 -*-
"""Extract every embedded .ff zone from a CODOL .ifs package.

Layout (measured): 0x00 'nifs', 0x04 u32 header length, 0x4c u64 tail length,
then a plaintext manifest of '<name>.ff' lines, then the first 'IWff0100'
payload; further zones follow back-to-back up to (len - tail_len).
"""
import struct, sys, io, os, re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

P = sys.argv[1]
OUT = sys.argv[2]
os.makedirs(OUT, exist_ok=True)

d = open(P, 'rb').read()
hdr = struct.unpack_from('<I', d, 4)[0]
tail_len = struct.unpack_from('<Q', d, 0x4c)[0]
end = len(d) - tail_len

man = d[hdr:d.find(b'IWff0100', hdr)].decode('latin-1', 'replace')
names = [line for line in man.splitlines() if line.strip()]
print('ifs', os.path.basename(P), len(d), 'manifest lines', len(names))

pos = d.find(b'IWff0100', hdr)
frames = []
while pos >= 0 and pos < end:
    # next zone boundary: scan for the next IWff0100
    nxt = d.find(b'IWff0100', pos + 8)
    if nxt < 0 or nxt > end:
        nxt = end
    frames.append((pos, nxt))
    pos = nxt
print('embedded zones:', len(frames))
for k, (a, b) in enumerate(frames[:12]):
    nm = names[k + 1] if k + 1 < len(names) else '?'
    print('  zone %2d  %#010x..%#010x  %9d bytes  %s' % (k, a, b, b - a, nm))

if len(sys.argv) > 3 and sys.argv[3] == '--extract':
    for k, (a, b) in enumerate(frames):
        nm = names[k + 1] if k + 1 < len(names) else 'zone%d' % k
        nm = nm.split('/')[-1]
        if not nm.endswith('.ff'):
            nm += '.ff'
        open(os.path.join(OUT, nm), 'wb').write(d[a:b])
    print('extracted', len(frames), 'to', OUT)
