import sys, os, struct, zlib, importlib.util, collections, math
sys.path.insert(0, r"_PLAINTEXT_PROJECT\tools")
spec = importlib.util.spec_from_file_location("cod", r"_PLAINTEXT_PROJECT\tools\codol_ff_decrypt.py")
cod = importlib.util.module_from_spec(spec); spec.loader.exec_module(cod)

print("=== KEY TEST: is layer1 body = AES-CTR( layer2 ) where layer2 is ALSO encrypted? ===")
print("Hypothesis: TWO chained ciphers with the SAME key but different IV.")
print("If so, XOR of body with AES-CTR(body) would reveal layer2 structure.\n")

p = cod.decrypt_layer1(r"COD OL\main\mp_playlists.ff")["plain"]
key = bytes.fromhex("da135e91c7981459a13ddc2aed3050ae6dd9a7ce619bb6c5")
iv  = cod.decrypt_layer1(r"COD OL\main\mp_playlists.ff")["iv"]
b = p[0x14C:]

def H(x):
    c=collections.Counter(x); n=len(x)
    return -sum((v/n)*math.log2(v/n) for v in c.values()) if n else 0.0

print("layer1 body H = %.4f" % H(b))

# candidate IVs to try "re-decrypting"
cands = {
  "same iv": iv,
  "zero": bytes(16),
  "iv+1": bytes.fromhex("ff6c10c6db650000149c1f0103000001"),
}
for nm, ivv in cands.items():
    d = cod.aes_ctr(b, key, ivv)
    print("   decrypt(%s) -> H=%.4f  head=%s" % (nm, H(d[:1<<18]), d[:16].hex()))

print("\n=== TEST: is the KEYS payload actually TWO keys (24+16) or (16+16) unused? ===")
raw = open(r"COD OL\main\mp_playlists.ff","rb").read()
n,d = cod.private_key()
pl = cod.rsa_unwrap(n,d, raw[0x15:0x15+256])
print("   payload len", len(pl), "hex", pl.hex())
print("   [0:16] ", pl[0:16].hex())
print("   [8:24] ", pl[8:24].hex())
print("   [16:32]", pl[16:32].hex())
print("   [24:40]", pl[24:40].hex())

print("\n=== TEST: try AES-128 with payload[0:16] and [24:40] as key, ctr from zero ===")
for kn, k in (("pl[0:16]", pl[0:16]), ("pl[8:24]", pl[8:24]), ("pl[24:40]", pl[24:40])):
    for ivn, ivv in (("pl[16:32]", pl[16:32]), ("zero", bytes(16))):
        try:
            dd = cod.aes_ctr(b[:1<<20], k, ivv)
            print("   key=%s iv=%-10s H=%.4f head=%s" % (kn, ivn, H(dd[:1<<18]), dd[:16].hex()))
        except Exception as e:
            print("   key=%s iv=%s ERR %s" % (kn, ivn, e))
