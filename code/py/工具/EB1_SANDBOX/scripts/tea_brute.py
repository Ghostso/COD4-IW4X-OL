# Brute-force TEA variants against TCLS cfg files
import struct, os

DELTA = 0x9E3779B9

def tea_dec_block(v0, v1, k, rounds, endian):
    s = (DELTA * rounds) & 0xFFFFFFFF
    for _ in range(rounds):
        v1 = (v1 - ((((v0 << 4) & 0xFFFFFFFF) + k[2] & 0xFFFFFFFF) ^ ((v0 + s) & 0xFFFFFFFF) ^ (((v0 >> 5) + k[3]) & 0xFFFFFFFF))) & 0xFFFFFFFF
        v0 = (v0 - ((((v1 << 4) & 0xFFFFFFFF) + k[0] & 0xFFFFFFFF) ^ ((v1 + s) & 0xFFFFFFFF) ^ (((v1 >> 5) + k[1]) & 0xFFFFFFFF))) & 0xFFFFFFFF
        s = (s - DELTA) & 0xFFFFFFFF
    return v0, v1

def xtea_dec_block(v0, v1, k, rounds, endian):
    s = (DELTA * rounds) & 0xFFFFFFFF
    for _ in range(rounds):
        v1 = (v1 - ((((v0 << 4) & 0xFFFFFFFF) ^ (v0 >> 5)) + v0 ^ s + k[(s >> 11) & 3])) & 0xFFFFFFFF
        s = (s - DELTA) & 0xFFFFFFFF
        v0 = (v0 - ((((v1 << 4) & 0xFFFFFFFF) ^ (v1 >> 5)) + v1 ^ s + k[s & 3])) & 0xFFFFFFFF
    return v0, v1

def score(b):
    return sum(1 for c in b if c in (9, 10, 13) or 32 <= c < 127)

def try_all(path, keybytes):
    d = open(path, 'rb').read()[:0x100]
    results = []
    for endian in ('>', '<'):
        k = struct.unpack(endian + '4I', keybytes)
        for name, fn in (('TEA', tea_dec_block), ('XTEA', xtea_dec_block)):
            for rounds in (16, 32, 64):
                for mode in ('ECB', 'CBC'):
                    out = bytearray()
                    prev = b'\0' * 8
                    ok = True
                    for i in range(0, len(d) - 7, 8):
                        blk = d[i:i+8]
                        v0, v1 = struct.unpack(endian + '2I', blk)
                        v0, v1 = fn(v0, v1, k, rounds, endian)
                        dec = struct.pack(endian + '2I', v0, v1)
                        if mode == 'CBC':
                            dec = bytes(a ^ b for a, b in zip(dec, prev))
                            prev = blk
                        out += dec
                    sc = score(bytes(out))
                    results.append((sc, endian, name, rounds, mode, bytes(out)))
    results.sort(key=lambda r: -r[0])
    print('=====', path, 'key', keybytes)
    for sc, endian, name, rounds, mode, out in results[:4]:
        print(sc, endian, name, rounds, mode, repr(out[:120]))

base = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
cfg = os.path.join(base, r'TCLS\config\commonconfig.cfg')
try_all(cfg, b'1111111111111111')
try_all(cfg, b'configconfigconf')
