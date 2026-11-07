# Decrypt TCLS config .cfg files (TEA, 16 rounds, big-endian, key from TCLS init)
import struct, sys, os

def tea_dec(data: bytes, key: bytes) -> bytes:
    k = struct.unpack('>4I', key)
    out = bytearray()
    for i in range(0, len(data) - 7, 8):
        v0, v1 = struct.unpack('>2I', data[i:i+8])
        s = (0x9E3779B9 * 16) & 0xFFFFFFFF
        for _ in range(16):
            v1 = (v1 - ((((v0 << 4) & 0xFFFFFFFF) + k[2] & 0xFFFFFFFF) ^ ((v0 + s) & 0xFFFFFFFF) ^ (((v0 >> 5) + k[3]) & 0xFFFFFFFF))) & 0xFFFFFFFF
            v0 = (v0 - ((((v1 << 4) & 0xFFFFFFFF) + k[0] & 0xFFFFFFFF) ^ ((v1 + s) & 0xFFFFFFFF) ^ (((v1 >> 5) + k[1]) & 0xFFFFFFFF))) & 0xFFFFFFFF
            s = (s - 0x9E3779B9) & 0xFFFFFFFF
        out += struct.pack('>2I', v0, v1)
    return bytes(out)

KEY = b'1111111111111111'
base = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
for rel in [r'TCLS\config\commonconfig.cfg', r'TCLS\config\dirsystemconfig.cfg']:
    p = os.path.join(base, rel)
    d = open(p, 'rb').read()
    r = tea_dec(d, KEY)
    print('====', rel, 'size', len(d))
    print(repr(r[:300]))
    outname = os.path.join(base, '..', 'analysis_logs', os.path.basename(p) + '.dec')
    open(outname, 'wb').write(r)
    print('wrote', outname)
