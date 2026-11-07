import sys, os, struct, importlib.util, collections, math
sys.path.insert(0, r"CODOLServer\_mainline")
spec = importlib.util.spec_from_file_location("ff", r"CODOLServer\_mainline\ff_iw4_decrypt.py")
ff = importlib.util.module_from_spec(spec); spec.loader.exec_module(ff)
p = ff.decrypt_file(r"COD OL\main\mp_playlists.ff")["plain"]

lows = sum(1 for b in p if b < 0x40); hi = sum(1 for b in p if b>=0x80)
print("len=%d  <0x40=%d (%.2f%%)  >=0x80=%d (%.2f%%)  zeros=%d" % (
    len(p), lows, 100*lows/len(p), hi, 100*hi/len(p), p.count(0)))

print("\n=== hypothesis A: 6-bit packed (values 0..63) ===")
print("   if data were 6-bit, top 2 bits would be ~0 but not always")
clip = sum(1 for b in p[64:] if b < 64)
print("   bytes<64 in body[64:]: %d/%d = %.2f%%" % (clip, len(p)-64, 100*clip/(len(p)-64)))

print("\n=== hypothesis B: nibble-stream / high nibble mostly 0-3 ===")
hn = collections.Counter(b>>4 for b in p)
print("   high-nibble histogram:", dict(sorted(hn.items())))
ln = collections.Counter(b&0xF for b in p)
print("   low-nibble histogram :", dict(sorted(ln.items())))

print("\n=== hypothesis C: this is the STRUCTURE region; find where it ends ===")
# measure <0x40 ratio in 256-byte windows
print("   window     <0x40%%   H")
for off in range(0, min(len(p), 8192), 512):
    w = p[off:off+512]
    r = 100*sum(1 for b in w if b<0x40)/len(w)
    c = collections.Counter(w); n=len(w)
    h = -sum((v/n)*math.log2(v/n) for v in c.values())
    print("   %6d   %6.2f%%   %.3f" % (off, r, h))

print("\n=== hypothesis D: the hidden container - look for repeated 4-byte alignment markers ===")
# CODOl / IW engine assets often have 4-byte aligned named blocks
for off in range(0, 512, 4):
    v = struct.unpack_from("<I", p, off)[0]
    if 0 < v < 0x10000:
        print("   +0x%03x u32=%d (0x%x)  bytes=%s" % (off, v, v, p[off:off+4].hex()))

print("\n=== hypothesis E: is the visible 'mp_playlists' at 300 the zone name record? dump +256..+512 ===")
seg = p[256:512]
for r in range(0, len(seg), 16):
    b = seg[r:r+16]
    print("   +0x%03x  %s  %s" % (256+r, b.hex(), ''.join(chr(x) if 32<=x<127 else '.' for x in b)))
