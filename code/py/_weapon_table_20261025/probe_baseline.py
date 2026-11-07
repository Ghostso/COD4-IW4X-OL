# -*- coding: utf-8 -*-
"""Probe a retail gamestate baseline file (IWCB000) for readable weapon names
and byte statistics, across several offsets."""
import sys, io, re, collections, math

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

P = sys.argv[1]
d = open(P, 'rb').read()
print('file', P, len(d), 'bytes')
print('head', d[:16].hex(), d[:8])

body = d[0x10:]
hist = collections.Counter(body)
H = -sum((c / len(body)) * math.log2(c / len(body)) for c in hist.values())
print('body entropy %.4f  (<0x40)=%.2f%%  (>=0x80)=%.2f%%'
      % (H, 100.0 * sum(1 for b in body if b < 0x40) / len(body),
         100.0 * sum(1 for b in body if b >= 0x80) / len(body)))

for probe in (b'_mp\x00', b'weapon', b'defaultweapon', b'm4', b'ak47', b'.csv',
              b'none\x00', b'mp/'):
    n = d.count(probe)
    print('%-16r %d' % (probe, n))

print('\nlongest printable runs:')
runs = sorted((len(m.group()), m.start(), m.group()[:60])
              for m in re.finditer(rb'[ -~]{4,}', d))
for ln, off, s in runs[-12:]:
    print('  %#08x len=%-3d %r' % (off, ln, s))

print('\nword-ish tokens (letters+digits+_ , len>=5):')
toks = collections.Counter(
    m.group().decode('latin-1')
    for m in re.finditer(rb'[A-Za-z][A-Za-z0-9_]{4,30}', d))
for t, c in toks.most_common(25):
    print('  %-32s %d' % (t, c))
