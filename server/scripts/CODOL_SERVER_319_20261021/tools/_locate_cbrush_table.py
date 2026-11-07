"""Locate the cbrush_t table in mp_firingrange_zone.bin by cross-checking
against the brushside table it must reference.

IW4X cbrush_t (36 bytes):
    u16 numsides; u16 glassPieceIndex; cbrushside_t* sides;
    u8* baseAdjacentSide; u16 axialMaterialNum[2][3];
    u8 firstAdjacentSideOffsets[2][3]; u8 edgeCount[2][3];

Constraint used: every brush's `sides` pointer must land inside the verified
brushside table, must be 8-byte aligned, and consecutive brushes must tile the
table without gaps (brush[i].sides + numsides*8 == brush[i+1].sides).
"""
import struct
import sys

ZONE = r'_map_extract\mp_firingrange_zone.bin'
PLANES_OFF, PLANE_COUNT = 5001523, 7587
SIDES_OFF, SIDE_COUNT = 42720480, 18770
DELTA = 0x2FE4FC1E

d = open(ZONE, 'rb').read()
N = len(d)
side_base = DELTA + SIDES_OFF            # absolute ptr value of sides[0]
side_end = side_base + SIDE_COUNT * 8


def u16(o):
    return struct.unpack_from('<H', d, o)[0]


def u32(o):
    return struct.unpack_from('<I', d, o)[0]


def brush_ok(o):
    """Does a 36-byte record at o look like a cbrush_t that tiles the side table?"""
    if o + 36 > N:
        return None
    numsides = u16(o)
    sp = u32(o + 4)
    if numsides == 0 or numsides > 64:
        return None
    if not (side_base <= sp < side_end):
        return None
    if (sp - side_base) % 8 != 0:
        return None
    return numsides, sp


# Find runs where consecutive brushes tile the side table exactly.
best = []
i = 0
while i < N - 36:
    first = brush_ok(i)
    if not first:
        i += 4
        continue
    run = []
    o = i
    expect = first[1]
    while True:
        r = brush_ok(o)
        if not r or r[1] != expect:
            break
        run.append((o, r[0], r[1]))
        expect = r[1] + r[0] * 8
        o += 36
        if o + 36 > N:
            break
    if len(run) >= 20:
        best.append((i, run))
        i = o
    else:
        i += 4

print('candidate runs (>=20 brushes tiling the side table): %d' % len(best))
for off, run in best[:5]:
    span = run[-1][2] + run[-1][1] * 8 - side_base
    print('  offset=%d  brushes=%d  covers %d/%d side slots'
          % (off, len(run), span // 8, SIDE_COUNT))

if best:
    off, run = max(best, key=lambda x: len(x[1]))
    print('\nBEST: cbrush table at file offset %d, %d brushes' % (off, len(run)))
    print('      first 3: %s' % [(b[1], hex(b[2])) for b in run[:3]])
