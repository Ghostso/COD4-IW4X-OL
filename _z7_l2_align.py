import sys, os, struct, zlib, importlib.util, collections, math
sys.path.insert(0, r"CODOLServer\_mainline")
spec = importlib.util.spec_from_file_location("ff", r"CODOLServer\_mainline\ff_iw4_decrypt.py")
ff = importlib.util.module_from_spec(spec); spec.loader.exec_module(ff)

def load(name):
    return ff.decrypt_file(os.path.join("COD OL","main",name))["plain"]

def H(b):
    c=collections.Counter(b); n=len(b)
    return -sum((v/n)*math.log2(v/n) for v in c.values()) if n else 0.0

a = load("mp_playlists.ff")
b = load("localized_ui_mp.ff")
print("mp_playlists   len", len(a), "H", round(H(a),4))
print("localized_ui   len", len(b), "H", round(H(b),4))

# head region entropy at fine granularity
print("\n=== mp_playlists fine entropy 0..256 ===")
for off in range(0, 256, 16):
    print("  +0x%03x H=%.3f %s" % (off, H(a[off:off+16]), a[off:off+16].hex()))

print("\n=== does a repeating keystream exist? xor plaintext self at lag L, H(xor) ===")
for L in [1,2,3,4,8,12,16,20,24,32,64,128,256,512,4096]:
    x = bytes(a[i]^a[i+L] for i in range(min(len(a)-L, 20000)))
    print("  lag %-5d H(xor)=%.4f  (random=8.0; low => structure)" % (L, H(x)))

print("\n=== 16-byte block alignment test: is head[8:24] a block boundary? ===")
for k in range(0, 48, 8):
    print("  row %2d: %s" % (k, a[k:k+16].hex()))

print("\n=== scan whole body for 'IWff' / 'zone' / known COD asset names ===")
for pat in (b"IWff", b"zone", b"material", b"image", b"sound", b"xmodel", b"weapon", b"techset"):
    idxs=[]
    st=0
    while True:
        j=a.find(pat, st)
        if j<0 or len(idxs)>=5: break
        idxs.append(j); st=j+1
    print("  %-10s %s" % (pat.decode(), idxs if idxs else "none"))

print("\n=== per-file key check: all files same key, different IV -> different keystream ===")
# if keystream were fixed, a[8:] ^ b[8:] at same offset would be plaintext^plaintext
n = min(len(a), len(b)) - 8
print("  head byte diff a[8..24] vs b[8..24] identical?", a[8:24]==b[8:24])
