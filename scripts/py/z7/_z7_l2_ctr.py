import sys, os, struct, importlib.util
sys.path.insert(0, r"CODOLServer\_mainline")
spec = importlib.util.spec_from_file_location("ff", r"CODOLServer\_mainline\ff_iw4_decrypt.py")
ff = importlib.util.module_from_spec(spec); spec.loader.exec_module(ff)
from Crypto.Cipher import AES

raw = open(r"COD OL\main\mp_playlists.ff","rb").read()
n,d = ff.private_key()
payload = ff.rsa_decrypt_key(n,d, raw[0x15:0x15+256])
key, iv = bytes(payload[:24]), bytes(payload[24:40])
print("key", key.hex(), "iv", iv.hex())

def ctr(data, key, iv, skip=0):
    aes = AES.new(key, AES.MODE_ECB); ctr=[b for b in iv]
    for _ in range(skip):
        for x in range(16):
            ctr[x]=(ctr[x]+1)&0xFF
            if ctr[x]: break
    out=bytearray(len(data))
    for off in range(0,len(data),16):
        ks=aes.encrypt(bytes(ctr))
        for i,b in enumerate(data[off:off+16]): out[off+i]=b^ks[i]
        for x in range(16):
            ctr[x]=(ctr[x]+1)&0xFF
            if ctr[x]: break
    return bytes(out)

# current script: ciphertext starts at 0x115, ctr from iv  -> we already have this
# alt: the 4 zero bytes are DECRYPTED from a keystream block => ctr starts one block EARLIER
print()
print("=== Variant 1: ctr skip=0, skip=1,2,3 on body at 0x115 (look at +8..+16 region) ===")
body = raw[0x115:]
for s in (0,1,2,3,4):
    o = ctr(body[:64], key, iv, s)
    print("  skip=%d  +8:16=%s  ascii=%r" % (s, o[8:16].hex(), o[8:16]))

print()
print("=== Variant 2: the 4-byte field is a BIG-ENDIAN u32 (block counter) ===")
# if head[8:12] = high bytes of a big-endian counter, keystream block0 could be counter=0
for s in (0,):
    o = ctr(body[:64], key, iv, s)
    print("   head after ctr:", o[:16].hex())

print()
print("=== Variant 3: is the IV itself the counter for block 0, and head[8:12] is bit-field of IV? ===")
# try interpreting head[8:12] as the top 4 bytes of a 128-bit BE counter starting from 0
for endian in ("little","big"):
    ivv = int.from_bytes(iv, endian)
    print("  iv as %s int = %d" % (endian, ivv))

print()
print("=== DECISIVE: identical head[8:12]=00000000 across 10 files => check raw[0x121:0x125] ===")
for nm in ["ui_mp.ff","code_post_gfx_mp.ff","localized_ui_mp.ff"]:
    r = open(os.path.join("COD OL","main",nm),"rb").read(0x130)
    print("  %-26s raw[0x11d:0x129] = %s" % (nm, r[0x11d:0x129].hex()))
