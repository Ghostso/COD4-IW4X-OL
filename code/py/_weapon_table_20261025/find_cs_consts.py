# -*- coding: utf-8 -*-
"""Find cs index -> weapon name assignment inside the client by looking for the
CS_WEAPONS base 5362/5363 constants used as imm32 in the loaded EXE, and for
the array of per-configstring type bytes mentioned in project notes
(0x77D8250, length 0x31D9)."""
import struct, sys, io, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

EXE = sys.argv[1]
d = open(EXE, 'rb').read()
e_lfanew = struct.unpack_from('<I', d, 0x3C)[0]
nsec = struct.unpack_from('<H', d, e_lfanew + 6)[0]
opt = e_lfanew + 24
image_base = struct.unpack_from('<I', d, opt + 28)[0]
sh = opt + struct.unpack_from('<H', d, e_lfanew + 20)[0]
secs = []
for i in range(nsec):
    o = sh + i * 40
    name = d[o:o + 8].rstrip(b'\0').decode('latin-1')
    vsz, va, rsz, rptr = struct.unpack_from('<IIII', d, o + 8)
    secs.append((name, va, vsz, rptr, rsz))
print('image_base', hex(image_base))


def off_to_va(off):
    for name, va, vsz, rptr, rsz in secs:
        if rptr <= off < rptr + rsz:
            return image_base + va + (off - rptr)
    return None


def va_to_off(va):
    if va < image_base:
        return None
    r = va - image_base
    for name, sva, vsz, rptr, rsz in secs:
        if sva <= r < sva + max(vsz, rsz):
            off = rptr + (r - sva)
            if off < len(d):
                return off
    return None


for label, va in (('cs type table 0x77D8250', 0x77D8250),
                  ('weapon count cs byte 0x77DB226', 0x77DB226)):
    off = va_to_off(va)
    print('%-32s va=%#x -> file %s' % (label, va, hex(off) if off else 'NOT MAPPED'))
    if off:
        row = d[off:off + 32]
        print('   bytes:', ' '.join('%02x' % b for b in row))

for const in (5362, 5363, 6517, 12246, 0x31D9, 700, 0x2BC):
    needle = struct.pack('<I', const)
    hits = []
    i = 0
    while True:
        i = d.find(needle, i)
        if i < 0:
            break
        hits.append(i)
        i += 1
        if len(hits) > 40:
            break
    print('const %-6d (0x%x): %d hits %s' % (const, const, len(hits),
                                             [hex(h) for h in hits[:8]]))
