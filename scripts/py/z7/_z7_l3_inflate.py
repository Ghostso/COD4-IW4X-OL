import sys, os, struct, zlib, importlib.util
sys.path.insert(0, r"CODOLServer\_mainline")
spec = importlib.util.spec_from_file_location("ff", r"CODOLServer\_mainline\ff_iw4_decrypt.py")
ff = importlib.util.module_from_spec(spec); spec.loader.exec_module(ff)
from Crypto.Cipher import AES

raw = open(r"COD OL\main\mp_playlists.ff","rb").read()
n,d = ff.private_key()
payload = ff.rsa_decrypt_key(n,d, raw[0x15:0x15+256])
key, iv = bytes(payload[:24]), bytes(payload[24:40])
print("key", key.hex())
print("iv ", iv.hex())

def ctr_since_zero(data, key, iv):
    aes = AES.new(key, AES.MODE_ECB); c=[b for b in iv]
    out=bytearray(len(data))
    for off in range(0,len(data),16):
        ks=aes.encrypt(bytes(c))
        for i,b in enumerate(data[off:off+16]): out[off+i]=b^ks[i]
        for x in range(16):
            c[x]=(c[x]+1)&0xFF
            if c[x]: break
    return bytes(out)

body = raw[0x115:]
dec = ctr_since_zero(body, key, iv)
print("body len", len(body))
print("dec[0:16]", dec[:16].hex(), repr(dec[:16]))

# Now: is it zlib? try inflate on the decrypted body
print()
print("=== inflate(decrypted body) ===")
for tag, st in (("whole", 0), ("skip12", 12), ("skip0",0)):
    for wb in (15,-15,47):
        try:
            o = zlib.decompressobj(wb).decompress(dec[st:])
            if len(o)>0: print("  %s wbits=%d -> %d bytes" % (tag,wb,len(o)))
        except Exception as e:
            pass

# try skipping 12 bytes AND resetting ctr after first 12
print()
print("=== treat first 12 bytes plaintext, ctr from 12 onward starting at iv ===")
alt = dec[:12] + ctr_since_zero(body[12:], key, iv)
print("  alt[:32]", alt[:32].hex())
for wb in (15,-15,47):
    try:
        o = zlib.decompressobj(wb).decompress(alt)
        if len(o)>64: print("  alt wbits=%d -> %d bytes  %r" % (wb,len(o),o[:48]))
    except Exception: pass

print()
print("=== try 8192-block CTR reset (per AuthLoadInflateDecryptBaseFunc) ===")
def ctr_blocks(data,key,iv,bs=8192):
    out=bytearray()
    for s in range(0,len(data),bs):
        out += ctr_since_zero(data[s:s+bs],key,iv)
    return bytes(out)
rb = ctr_blocks(body,key,iv)
for wb in (15,-15,47):
    try:
        o = zlib.decompressobj(wb).decompress(rb)
        if len(o)>64: print("  8192-reset wbits=%d -> %d bytes  %r" % (wb,len(o),o[:48]))
    except Exception as e: pass

print()
print("=== scan: does any 12-aligned offset in dec have zlib header 78 xx / 1f8b ===")
for off in range(0, 4096, 2):
    if dec[off]==0x78 and dec[off+1] in (0x01,0x5e,0x9c,0xda):
        print("   candidate zlib @0x%x : %s" % (off, dec[off:off+8].hex()))
    if dec[off]==0x1f and dec[off+1]==0x8b:
        print("   gzip @0x%x" % off)
