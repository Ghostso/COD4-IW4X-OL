import sys, os, struct, zlib, importlib.util, collections, math
sys.path.insert(0, r"_PLAINTEXT_PROJECT\tools")
spec = importlib.util.spec_from_file_location("cod", r"_PLAINTEXT_PROJECT\tools\codol_ff_decrypt.py")
cod = importlib.util.module_from_spec(spec); spec.loader.exec_module(cod)

def H(b):
    c=collections.Counter(b); n=len(b)
    return -sum((v/n)*math.log2(v/n) for v in c.values()) if n else 0.0

print("=== compare layer1 output entropy: small vs large ff ===")
for nm in ["mp_playlists.ff","development_mp.ff","code_pre_gfx_mp.ff","localized_ui_mp.ff","ui_mp.ff"]:
    i = cod.decrypt_layer1(os.path.join("COD OL","main",nm))
    p = i["plain"]
    b = p[0x14C:]
    print("  %-26s len=%9d  H(head1MB)=%.4f  H(body)=%.4f  body0..32=%s" % (
        nm, len(p), H(p[:1<<20]), H(b[:1<<20]), b[:32].hex()))

print()
print("=== mp_playlists body: locate structured regions ===")
p = cod.decrypt_layer1(r"COD OL\main\mp_playlists.ff")["plain"]
b = p[0x14C:]
print("  body len", len(b))
for off in range(0, min(len(b), 4096), 128):
    w = b[off:off+128]
    print("   %5d H=%.3f <0x40=%3d  %s" % (off, H(w), sum(1 for x in w if x<0x40),
          ''.join(chr(x) if 32<=x<127 else '.' for x in w[:48])))
