CONST = bytes.fromhex("ad42f59088a421e63bc9890239ff02dc110477ffee88620d")
# permutation groups as read from the disassembly (6,6,6,5)
PERM = [8,0x12,9,0xE,5,0x14,   0xA,7,0xB,0xC,0x15,0x16,
        0xD,0x10,3,0,1,0xF,     0x13,0x11,0x17,6,4]

def xform(src: bytes, decrypt: bool) -> bytes:
    """Reimplementation of 0xBA05A0.

    The routine walks 4 groups of 6 bytes.  For each position i it takes
    CONST[perm[i]] and XORs it with the source byte, writing the result.
    decrypt=True  : reads src (cipher) -> out (plain)   (0xBA06E8 branch)
    decrypt=False : writes out from src                 (0xBA06A2 branch)
    In practice the two branches differ only in which buffer is read/written,
    so the transformation is its own inverse at the byte level.
    """
    out = bytearray(len(src))
    for i, p in enumerate(PERM[:len(src)]):
        out[i] = src[i] ^ CONST[p]
    return bytes(out)

data = bytes(range(24))
e = xform(data, False)
d = xform(e, True)
print("src ", data.hex())
print("enc ", e.hex())
print("dec ", d.hex())
print("roundtrip ok:", d == data)
