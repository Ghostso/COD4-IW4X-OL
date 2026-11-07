"""Print the AES-128 key schedule for an all-zero key (176 bytes)."""
from __future__ import annotations


def expand_key(key: bytes) -> bytes:
    sbox = []
    p = q = 1
    sbox = [0] * 256
    while True:
        # compute multiplicative inverse in GF(2^8), then affine transform
        p = p ^ ((p << 1) & 0xFF) ^ (0x1B if p & 0x80 else 0)
        q ^= q << 1
        q ^= q << 2
        q ^= q << 4
        q &= 0xFF
        if q & 0x80:
            q ^= 0x09
        x = q ^ ((q << 1) | (q >> 7)) ^ ((q << 2) | (q >> 6)) ^ \
            ((q << 3) | (q >> 5)) ^ ((q << 4) | (q >> 4))
        sbox[p] = (x ^ 0x63) & 0xFF
        if p == 1:
            break
    sbox[0] = 0x63
    rcon = 1
    w = [list(key[i:i + 4]) for i in range(0, 16, 4)]
    for i in range(4, 44):
        temp = w[i - 1][:]
        if i % 4 == 0:
            temp = temp[1:] + temp[:1]
            temp = [sbox[b] for b in temp]
            temp[0] ^= rcon
            rcon = ((rcon << 1) ^ (0x11B if rcon & 0x80 else 0)) & 0xFF
        w.append([w[i - 4][j] ^ temp[j] for j in range(4)])
    return bytes(b for word in w for b in word)


print(expand_key(bytes(16)).hex())
