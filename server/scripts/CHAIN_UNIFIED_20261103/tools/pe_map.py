import struct, sys

def load(p):
    d = open(p, 'rb').read()
    pe = struct.unpack_from('<I', d, 0x3c)[0]
    nsec = struct.unpack_from('<H', d, pe + 6)[0]
    opt = struct.unpack_from('<H', d, pe + 0x14)[0]
    ib = struct.unpack_from('<I', d, pe + 0x34)[0]
    secs = []
    so = pe + 0x18 + opt
    for i in range(nsec):
        o = so + 40 * i
        vs, va, rs, ra = struct.unpack_from('<IIII', d, o + 8)
        secs.append((va, vs, ra, rs))
    return d, ib, secs

def va2off(secs, ib, va):
    rva = va - ib
    for va_, vs, ra, rs in secs:
        if va_ <= rva < va_ + max(vs, rs):
            off = ra + (rva - va_)
            if off < 0 or off >= (1 << 40):
                return None
            return off
    return None

def stdin_main():
    p = sys.argv[1]
    d, ib, secs = load(p)
    for a in sys.argv[2:]:
        va = int(a, 16)
        off = va2off(secs, ib, va)
        print(hex(va), 'off', hex(off) if off is not None else None,
              d[off:off + 64].hex(' ') if off is not None else '')

if __name__ == '__main__':
    stdin_main()
