"""Scan the unpacked PE for E8/E9 references to a target VA, and dump disassembly-lite context."""
import struct, sys
sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from pe_map import load, va2off

P = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\UNPACKED_146\codoMP_unpacked_146.exe'
d, ib, secs = load(P)
target = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x7F4F10

hits = []
for (va_, vs, ra, rs) in secs:
    n = min(vs, rs)
    base_va = ib + va_
    seg = d[ra:ra + n]
    i = 0
    while True:
        i = seg.find(b'\xe8', i)
        if i < 0:
            break
        if i + 5 <= len(seg):
            rel = struct.unpack_from('<i', seg, i + 1)[0]
            tgt = base_va + i + 5 + rel
            if tgt == target:
                hits.append(base_va + i)
        i += 1
print('callers of %08X: %d' % (target, len(hits)))
for h in hits:
    off = va2off(secs, ib, h)
    print('  call at %08X   bytes: %s' % (h, d[off - 24:off + 40].hex(' ')))
