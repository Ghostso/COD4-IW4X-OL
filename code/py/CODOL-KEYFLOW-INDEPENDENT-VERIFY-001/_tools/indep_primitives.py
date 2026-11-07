# -*- coding: utf-8 -*-
"""CODOL-KEYFLOW-INDEPENDENT-VERIFY-001 : 独立原语层 (own SHA-1 / own HMAC-SHA1 / own AES-128)
每个原语都用 FIPS/RFC 规范自写，不使用 hashlib/hmac/cryptography。
仅用于与独立 oracle 交叉校验；不下结论。
"""
import struct

# ---------------- SHA-1 (FIPS 180-4) ----------------
def _sha1_pad(msg):
    ml = len(msg) * 8
    msg += b'\x80'
    while len(msg) % 64 != 56:
        msg += b'\x00'
    msg += struct.pack('>Q', ml)
    return msg

def sha1(msg):
    h = [0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0]
    for off in range(0, len(_sha1_pad(msg)), 64):
        w = list(struct.unpack('>16I', _sha1_pad(msg)[off:off+64]))
        for i in range(16, 80):
            w.append(_rol(w[i-3] ^ w[i-8] ^ w[i-14] ^ w[i-16], 1))
        a,b,c,d,e = h
        for i in range(80):
            if i < 20:   f, k = (b & c) | ((~b & 0xffffffff) & d), 0x5A827999
            elif i < 40: f, k = b ^ c ^ d, 0x6ED9EBA1
            elif i < 60: f, k = (b & c) | (b & d) | (c & d), 0x8F1BBCDC
            else:        f, k = b ^ c ^ d, 0xCA62C1D6
            t = (_rol(a,5) + f + e + k + w[i]) & 0xffffffff
            e,d,c,b,a = d,c,_rol(b,30),a,t
        h = [(x+y) & 0xffffffff for x,y in zip(h,[a,b,c,d,e])]
    return b''.join(struct.pack('>I', x) for x in h)

def _rol(x, n):
    return ((x << n) | (x >> (32-n))) & 0xffffffff

# ---------------- HMAC-SHA1 (RFC 2104) ----------------
def hmac_sha1(key, data):
    if len(key) > 64:
        key = sha1(key)
    key = key + b'\x00' * (64 - len(key))
    o_key = bytes(b ^ 0x5c for b in key)
    i_key = bytes(b ^ 0x36 for b in key)
    return sha1(o_key + sha1(i_key + data))

# ---------------- AES-128 (FIPS 197) ----------------
_SBOX = [
0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16]
_INV_SBOX = [0]*256
for i,v in enumerate(_SBOX): _INV_SBOX[v]=i

_RCON = [0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1b,0x36,0x6c,0xd8,0xab,0x4d]

def _xtime(a):
    a <<= 1
    if a & 0x100: a ^= 0x11b
    return a & 0xff

def _gmul(a,b):
    r=0
    for _ in range(8):
        if b & 1: r ^= a
        b >>= 1
        a = _xtime(a)
    return r & 0xff

def _key_expansion(key):
    assert len(key)==16
    w=[list(key[i*4:i*4+4]) for i in range(4)]
    for i in range(4,44):
        t=w[i-1][:]
        if i%4==0:
            t=t[1:]+t[:1]
            t=[_SBOX[x] for x in t]
            t[0]^=_RCON[i//4-1]
        w.append([w[i-4][j]^t[j] for j in range(4)])
    return w

def _add_round_key(s,w,rnd):
    for c in range(4):
        for r in range(4):
            s[r][c]^=w[rnd*4+c][r]

def _sub_bytes(s):
    for r in range(4):
        for c in range(4): s[r][c]=_SBOX[s[r][c]]

def _inv_sub_bytes(s):
    for r in range(4):
        for c in range(4): s[r][c]=_INV_SBOX[s[r][c]]

def _shift_rows(s):
    for r in range(1,4):
        s[r]=s[r][r:]+s[r][:r]

def _inv_shift_rows(s):
    for r in range(1,4):
        s[r]=s[r][-r:]+s[r][:-r]

def _mix_columns(s):
    for c in range(4):
        a=[s[r][c] for r in range(4)]
        s[0][c]=_gmul(a[0],2)^_gmul(a[1],3)^a[2]^a[3]
        s[1][c]=a[0]^_gmul(a[1],2)^_gmul(a[2],3)^a[3]
        s[2][c]=a[0]^a[1]^_gmul(a[2],2)^_gmul(a[3],3)
        s[3][c]=_gmul(a[0],3)^a[1]^a[2]^_gmul(a[3],2)

def _inv_mix_columns(s):
    for c in range(4):
        a=[s[r][c] for r in range(4)]
        s[0][c]=_gmul(a[0],14)^_gmul(a[1],11)^_gmul(a[2],13)^_gmul(a[3],9)
        s[1][c]=_gmul(a[0],9)^_gmul(a[1],14)^_gmul(a[2],11)^_gmul(a[3],13)
        s[2][c]=_gmul(a[0],13)^_gmul(a[1],9)^_gmul(a[2],14)^_gmul(a[3],11)
        s[3][c]=_gmul(a[0],11)^_gmul(a[1],13)^_gmul(a[2],9)^_gmul(a[3],14)

def _to_state(block):
    return [[block[c*4+r] for c in range(4)] for r in range(4)]

def _from_state(s):
    return bytes(s[r][c] for c in range(4) for r in range(4))

def aes128_encrypt_block(key, block):
    w=_key_expansion(key)
    s=_to_state(block)
    _add_round_key(s,w,0)
    for rnd in range(1,10):
        _sub_bytes(s); _shift_rows(s); _mix_columns(s); _add_round_key(s,w,rnd)
    _sub_bytes(s); _shift_rows(s); _add_round_key(s,w,10)
    return _from_state(s)

def aes128_decrypt_block(key, block):
    w=_key_expansion(key)
    s=_to_state(block)
    _add_round_key(s,w,10)
    for rnd in range(9,0,-1):
        _inv_shift_rows(s); _inv_sub_bytes(s); _add_round_key(s,w,rnd); _inv_mix_columns(s)
    _inv_shift_rows(s); _inv_sub_bytes(s); _add_round_key(s,w,0)
    return _from_state(s)

def aes128_cbc_encrypt(key, iv, pt):
    assert len(pt)%16==0 and len(iv)==16
    out=b''; prev=iv
    for i in range(0,len(pt),16):
        blk=bytes(a^b for a,b in zip(pt[i:i+16],prev))
        prev=aes128_encrypt_block(key,blk); out+=prev
    return out

def aes128_cbc_decrypt(key, iv, ct):
    assert len(ct)%16==0 and len(iv)==16
    out=b''; prev=iv
    for i in range(0,len(ct),16):
        blk=ct[i:i+16]
        out+=bytes(a^b for a,b in zip(aes128_decrypt_block(key,blk),prev))
        prev=blk
    return out

if __name__ == '__main__':
    print('sha1 empty   :', sha1(b'').hex())
    print('sha1 abc     :', sha1(b'abc').hex())
    print('hmac sha1 rfc:', hmac_sha1(bytes.fromhex('0b'*20), b'Hi There').hex())
    print('aes fips197  :', aes128_encrypt_block(bytes.fromhex('000102030405060708090a0b0c0d0e0f'),
          bytes.fromhex('00112233445566778899aabbccddeeff')).hex())
