import sys, os, struct, zlib, bz2, lzma, importlib.util, collections, math
sys.path.insert(0, r"CODOLServer\_mainline")
spec = importlib.util.spec_from_file_location("ff", r"CODOLServer\_mainline\ff_iw4_decrypt.py")
ff = importlib.util.module_from_spec(spec); spec.loader.exec_module(ff)

p = ff.decrypt_file(r"COD OL\main\ui_mp.ff")["plain"]
print("ui_mp layer1 len =", len(p))
print("head 0x00..0x30:", p[:0x30].hex())
print("head ascii     :", ''.join(chr(b) if 32<=b<127 else '.' for b in p[:0x30]))

body = p[0x14C:]
print("\nbody@0x14C len =", len(body))
print("body first 32:", body[:32].hex())

def H(b):
    c=collections.Counter(b); n=len(b)
    return -sum((v/n)*math.log2(v/n) for v in c.values()) if n else 0.0

print("\n=== entropy of ui_mp body in 64KiB windows (first 1MiB) ===")
for off in range(0, min(len(body), 1<<20), 1<<16):
    w = body[off:off+(1<<16)]
    print("   %9d  H=%.4f" % (off, H(w)))

print("\n=== global byte histogram of the whole body (top 20) ===")
c = collections.Counter(body)
tot = len(body)
for v,n in c.most_common(20):
    print("   0x%02x  %10d  %6.3f%%" % (v,n,100*n/tot))

print("\n=== zero fraction ===")
print("   zeros=%d (%.3f%%)  high(>=0x80)=%d (%.3f%%)" % (
    body.count(0), 100*body.count(0)/tot,
    sum(1 for b in body if b>=0x80), 100*sum(1 for b in body if b>=0x80)/tot))

print("\n=== try decompression on ui_mp body ===")
for tag, dd in (("zlib", zlib.decompressobj(15)),
                ("raw",  zlib.decompressobj(-15)),
                ("gzip", zlib.decompressobj(47))):
    try:
        o = dd.decompress(body[:1<<22])
        if len(o)>256: print("   %s -> %d bytes %r" % (tag, len(o), o[:40]))
        else: print("   %s -> %d bytes (too small)" % (tag, len(o)))
    except Exception as e:
        print("   %s -> %s" % (tag, type(e).__name__))
for tag, fn in (("bz2", bz2.decompress), ("lzma", lzma.decompress)):
    try:
        o = fn(body[:1<<22])
        print("   %s -> %d bytes" % (tag, len(o)))
    except Exception as e:
        print("   %s -> %s" % (tag, type(e).__name__))
