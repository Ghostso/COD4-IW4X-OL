import sys, os, struct, zlib, importlib.util, collections, math
sys.path.insert(0, r"_PLAINTEXT_PROJECT\tools")
spec = importlib.util.spec_from_file_location("cod", r"_PLAINTEXT_PROJECT\tools\codol_ff_decrypt.py")
cod = importlib.util.module_from_spec(spec); spec.loader.exec_module(cod)

p = cod.decrypt_layer1(r"COD OL\main\mp_playlists.ff")["plain"]
b = p[0x14C:]
print("body len", len(b))

# Does a MODERN compressor produce the same low-byte profile? Test with zlib levels.
print("\n=== compare byte-profile: real body vs zlib/raw-deflate of plausible data ===")
import random
random.seed(1)

def profile(x, label):
    lo = sum(1 for v in x if v < 0x40)/len(x)
    c=collections.Counter(x); n=len(x)
    h = -sum((v/n)*math.log2(v/n) for v in c.values())
    print("   %-24s len=%8d  H=%.4f  <0x40=%5.2f%%  >=0x80=%5.2f%%" % (
        label, len(x), h, 100*lo, 100*sum(1 for v in x if v>=0x80)/len(x)))

profile(b, "REAL mp_playlists body")
profile(os.urandom(len(b)), "os.urandom (ref random)")
# raw deflate of ascii-ish text
txt = (b"mp_playlists asset zone data 12345\n" * 2000)[:200000]
co = zlib.compressobj(9, zlib.DEFLATED, -15)
profile(co.compress(txt)+co.flush(), "raw-deflate(text)")
co = zlib.compressobj(9, zlib.DEFLATED, 15)
profile(co.compress(txt)+co.flush(), "zlib(text)")

print("\n=== HISTOGRAM comparison: real body vs raw-deflate(text) ===")
co = zlib.compressobj(9, zlib.DEFLATED, -15)
d = co.compress(txt)+co.flush()
h1 = collections.Counter(b); h2 = collections.Counter(d)
print("   real:  <0x40=%5.2f%%  <0x80=%5.2f%%  >=0x80=%5.2f%%" % (
    100*sum(h1[v] for v in range(0x40))/len(b),
    100*sum(h1[v] for v in range(0x80))/len(b),
    100*sum(h1[v] for v in range(0x80,256))/len(b)))
print("   defl:  <0x40=%5.2f%%  <0x80=%5.2f%%  >=0x80=%5.2f%%" % (
    100*sum(h2[v] for v in range(0x40))/len(d),
    100*sum(h2[v] for v in range(0x80))/len(d),
    100*sum(h2[v] for v in range(0x80,256))/len(d)))

print("\n=== the 4 zero bytes at body[0:4]: a u32 length? compare all files ===")
for nm in ["mp_playlists.ff","development_mp.ff","code_pre_gfx_mp.ff","localized_ui_mp.ff","ui_mp.ff","code_post_gfx_mp.ff"]:
    pp = cod.decrypt_layer1(os.path.join("COD OL","main",nm))["plain"]
    bd = pp[0x14C:]
    print("   %-26s body=%9d  u32@body[0]=%d  u32@body[4]=%d" % (
        nm, len(bd), struct.unpack_from("<I",bd,0)[0], struct.unpack_from("<I",bd,4)[0]))
