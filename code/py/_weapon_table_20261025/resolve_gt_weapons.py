# -*- coding: utf-8 -*-
"""Resolve type-28 weapon names in a zone by reading the asset's first dword as
a pointer relative to each plausible string block, then test index hypotheses.

WeaponDef layout (measured on common_mp.zone): dword 0 = name pointer,
localize key `SF_WEAPON_<NAME>_MP_NAME` at asset +0x101c for full defs.
For the small (4124-byte) gametype-zone defs the localize key is absent, so we
resolve the name pointer instead.
"""
import struct, re, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ZONE = sys.argv[1]
DIR_OFF = int(sys.argv[2], 0)
DIR_COUNT = int(sys.argv[3], 0)
ASSET_BASE = 0x28
KEY = re.compile(rb'SF_WEAPON_([A-Z0-9_]+)_MP_NAME')

d = open(ZONE, 'rb').read()
N = len(d)


def cstr_at(off, limit=96):
    if off < 0 or off >= N:
        return None
    e = d.find(b'\0', off, min(N, off + limit))
    if e <= off:
        return None
    s = d[off:e]
    if not re.fullmatch(rb'[A-Za-z0-9_./\-]{1,90}', s):
        return None
    return s.decode('latin-1')


rows = []
for i in range(DIR_COUNT):
    t, off, ptr, sz = struct.unpack_from('<4I', d, DIR_OFF + i * 16)
    if t != 28:
        continue
    start = ASSET_BASE + off
    b = d[start:start + sz]
    nm = None
    m = KEY.search(b)
    if m:
        nm = m.group(1).decode().lower() + '_mp'
    else:
        # first dword as a pointer into this zone, base candidates
        v = struct.unpack_from('<I', b, 0)[0]
        for base in (0, ASSET_BASE, 0x30000000, 0x30000028):
            cand = v - base
            s = cstr_at(cand)
            if s and s.endswith('_mp'):
                nm = s
                break
        if nm is None:
            # second dword
            v2 = struct.unpack_from('<I', b, 4)[0]
            for base in (0, ASSET_BASE, 0x30000000, 0x30000028):
                s = cstr_at(v2 - base)
                if s and s.endswith('_mp'):
                    nm = s
                    break
    rows.append((i, nm, sz))

print('type28', len(rows), 'named', sum(1 for _, n, _ in rows if n))
for k, (i, nm, sz) in enumerate(rows):
    print('  %3d dir=%-5d %-30s %d' % (k, i, nm or '?', sz))
