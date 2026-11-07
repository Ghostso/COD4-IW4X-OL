import sys, io, os, struct, zlib, bz2, lzma, math, collections
sys.path.insert(0, r"CODOLServer\_mainline")
import importlib.util
spec = importlib.util.spec_from_file_location("ff", r"CODOLServer\_mainline\ff_iw4_decrypt.py")
ff = importlib.util.module_from_spec(spec); spec.loader.exec_module(ff)

path = r"COD OL\main\mp_playlists.ff"
info = ff.decrypt_file(path)
plain = info["plain"]
print("plain len", len(plain))
print("head 64:", plain[:64].hex())
print("head asc:", ''.join(chr(b) if 32<=b<127 else '.' for b in plain[:64]))

def H(b):
    if not b: return 0.0
    c = collections.Counter(b)
    n = len(b)
    return -sum((v/n)*math.log2(v/n) for v in c.values())

print()
print("=== entropy profile (1KiB windows) ===")
for off in range(0, min(len(plain), 64*1024), 1024):
    w = plain[off:off+1024]
    s = ''.join(chr(b) if 32<=b<127 else '.' for b in w[:32])
    print("  %7d H=%.3f  %s" % (off, H(w), s))

print()
print("=== structural: u32 grid at 0x00..0x80 ===")
for o in range(0, 0x80, 4):
    print("  +0x%03x: %08x  %d" % (o, struct.unpack_from("<I", plain, o)[0], struct.unpack_from("<I", plain, o)[0]))

print()
print("=== try every zlib/gzip variant at every offset 0..4096 (level-agnostic) ===")
def try_zlib(buf, label):
    hits = []
    # raw deflate
    for wbits in (15, -15, 47, 31):
        try:
            d = zlib.decompressobj(wbits)
            out = d.decompress(buf[:1<<20])
            if len(out) > 64:
                hits.append((label, wbits, len(out), out[:32]))
        except Exception:
            pass
    return hits

found = False
for off in range(0, 4096):
    for tg, lab in ((b"\x78\x01","zlib78 01"),(b"\x78\x9c","zlib78 9c"),(b"\x78\xda","zlib78 da"),
                    (b"\x1f\x8b","gzip"),(b"\x5d\x00","lzma5d"),(b"BZh","bzip2")):
        if plain[off:off+len(tg)] == tg:
            print("  magic %s at %d" % (lab, off)); found = True
if not found:
    print("  no standard compression magic in first 4096 bytes")

print()
print("=== try zlib over the WHOLE body ignoring head, all offsets 8..64 ===")
for off in range(0, 128):
    for wb in (15, -15):
        try:
            d = zlib.decompressobj(wb)
            out = d.decompress(plain[off:off+400000])
            if len(out) > 256:
                print("  zlib wbits=%d off=%d -> %d bytes  %r" % (wb, off, len(out), out[:32]))
        except Exception:
            pass
