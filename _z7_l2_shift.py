import sys, os, struct, importlib.util, collections, math
sys.path.insert(0, r"CODOLServer\_mainline")
spec = importlib.util.spec_from_file_location("ff", r"CODOLServer\_mainline\ff_iw4_decrypt.py")
ff = importlib.util.module_from_spec(spec); spec.loader.exec_module(ff)

def H(b):
    c=collections.Counter(b); n=len(b)
    return -sum((v/n)*math.log2(v/n) for v in c.values()) if n else 0.0

p = ff.decrypt_file(r"COD OL\main\mp_playlists.ff")["plain"]

print("=== treat head[0:12] as PLAINTEXT, ciphertext starts at 12 ===")
print("  head:", p[0:12], p[:12].hex())
print("  body starts at 12; body_len =", len(p)-12)
print()
print("=== entropy of body in 16-byte blocks, first 40 (should be ~8.0 if cipher) ===")
for i in range(0, 640, 16):
    blk = p[12+i:12+i+16]
    print("   blk %3d (off %5d) H=%.3f %s" % (i//16, 12+i, H(blk), blk.hex()))

print()
print("=== KEY TEST: CTR restarts at block boundary 12?  Try decrypting body with ctr_start ===")
from Crypto.Cipher import AES
key = bytes.fromhex("da135e91c7981459a13ddc2aed3050ae6dd9a7ce619bb6c5")
iv  = bytes.fromhex("ff6c10c6db650000149c1f0103000000")

def ctr_from(body, key, iv, skip_blocks=0):
    aes = AES.new(key, AES.MODE_ECB)
    ctr = bytearray(iv)
    for _ in range(skip_blocks):
        for x in range(16):
            ctr[x] = (ctr[x]+1)&0xFF
            if ctr[x]: break
    out = bytearray(len(body))
    for off in range(0, len(body), 16):
        ks = aes.encrypt(bytes(ctr))
        for i,b in enumerate(body[off:off+16]):
            out[off+i] = b ^ ks[i]
        for x in range(16):
            ctr[x] = (ctr[x]+1)&0xFF
            if ctr[x]: break
    return bytes(out)

body = p[12:]
for skip in (0,1):
    d = ctr_from(body, key, iv, skip)
    s = ''.join(chr(b) if 32<=b<127 else '.' for b in d[:64])
    print("  skip=%d -> %s" % (skip, d[:48].hex()))
    print("           %s" % s)

print()
print("=== does the ORIGINAL (unshifted) keystream make head[8:12] decrypt to 0000? ===")
# original assumed body at 0x115; head[8:12] came out 00000000 which was plaintext-like
# => if cipher actually starts at 12, then head[8:12] must ALSO be ciphertext.
# Check: does XOR of head[8:12] with keystream block0 produce something sensible?
aes = AES.new(key, AES.MODE_ECB)
ks0 = aes.encrypt(iv)
print("  keystream blk0 =", ks0.hex())
print("  head[8:12] ^ ks0[8:12] =", bytes(p[8:12][i]^ks0[8+i] for i in range(4)).hex())
print("  head[12:16] ^ ks0[12:16] =", bytes(p[12:16][i]^ks0[12+i] for i in range(4)).hex())
