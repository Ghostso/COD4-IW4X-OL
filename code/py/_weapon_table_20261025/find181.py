# -*- coding: utf-8 -*-
"""Locate the '181 %s %d %d' error string in the client EXE and find code that
references it (push imm32 of its VA in the loaded image)."""
import struct, sys, io, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

EXE = sys.argv[1]
d = open(EXE, 'rb').read()
print('exe', os.path.basename(EXE), len(d))

# PE headers
e_lfanew = struct.unpack_from('<I', d, 0x3C)[0]
assert d[e_lfanew:e_lfanew + 4] == b'PE\0\0'
nsec = struct.unpack_from('<H', d, e_lfanew + 6)[0]
opt = e_lfanew + 24
image_base = struct.unpack_from('<I', d, opt + 28)[0]
print('image_base', hex(image_base), 'sections', nsec)

secs = []
sh = opt + struct.unpack_from('<H', d, e_lfanew + 20)[0]
for i in range(nsec):
    o = sh + i * 40
    name = d[o:o + 8].rstrip(b'\0').decode('latin-1')
    vsz, va, rsz, rptr = struct.unpack_from('<IIII', d, o + 8)
    secs.append((name, va, vsz, rptr, rsz))
    print('  %-8s va=%#010x vsz=%-9d raw=%#010x rsz=%d' % (name, va, vsz, rptr, rsz))


def off_to_va(off):
    for name, va, vsz, rptr, rsz in secs:
        if rptr <= off < rptr + rsz:
            return image_base + va + (off - rptr)
    return None


def va_to_off(va):
    r = va - image_base
    for name, sva, vsz, rptr, rsz in secs:
        if sva <= r < sva + max(vsz, rsz):
            return rptr + (r - sva)
    return None


for pat in (b'181 %s %d %d', b'181 %s %d %d\0'):
    off = d.find(pat)
    if off >= 0:
        va = off_to_va(off)
        print('string %r at file %#x -> va %s' % (pat, off, hex(va) if va else None))
        if va:
            needle = struct.pack('<I', va)
            hits = []
            i = 0
            while True:
                i = d.find(needle, i)
                if i < 0:
                    break
                hits.append(i)
                i += 1
            print('  imm32 references:', [hex(h) for h in hits[:10]])
            for h in hits[:5]:
                s = max(0, h - 40)
                print('  --- ref at %#x (%s) ---' % (h, hex(off_to_va(h) or 0)))
                for k in range(s, min(len(d), h + 24), 16):
                    row = d[k:k + 16]
                    print('    %#08x %-47s %s' % (k, ' '.join('%02x' % b for b in row),
                                                  ''.join(chr(b) if 32 <= b < 127 else '.' for b in row)))
        break
