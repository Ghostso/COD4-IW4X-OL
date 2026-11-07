import sys, os, struct, zlib, importlib.util, collections, math
sys.path.insert(0, r"_PLAINTEXT_PROJECT\tools")
spec = importlib.util.spec_from_file_location("cod", r"_PLAINTEXT_PROJECT\tools\codol_ff_decrypt.py")
cod = importlib.util.module_from_spec(spec); spec.loader.exec_module(cod)

def H(b):
    c=collections.Counter(b); n=len(b)
    return -sum((v/n)*math.log2(v/n) for v in c.values()) if n else 0.0

raw = open(r"COD OL\main\ui_mp.ff","rb").read()
key, iv = cod.recover_key(raw)
body = raw[0x115:]
l1 = cod.aes_ctr(body, key, iv)
print("key", key.hex())
print("H(layer1 first 1MB) = %.4f" % H(l1[:1<<20]))

print("\n=== TEST: CTR reset every N bytes ===")
def ctr_reset(data, key, iv, bs):
    out = bytearray()
    for s in range(0, len(data), bs):
        out += cod.aes_ctr(data[s:s+bs], key, iv)
    return bytes(out)
for bs in (4096, 8192, 16384, 32768):
    r = ctr_reset(body[:bs*4], key, iv, bs)
    print("   bs=%6d H=%.4f" % (bs, H(r[:min(len(r),1<<18)])))

print("\n=== zlib at aligned offsets, layer1 as-is ===")
for bs in (4096, 8192, 16384):
    hits=0
    for s in range(0, min(len(l1), bs*64), bs):
        for wb in (15,-15):
            try:
                o = zlib.decompressobj(wb).decompress(l1[s:s+bs])
                if len(o)>32:
                    hits+=1
                    if hits<=3: print("   bs=%d @%d wb=%d -> %d %r" % (bs,s,wb,len(o),o[:40]))
            except Exception: pass
    print("   bs=%d hits=%d" % (bs,hits))

print("\n=== global zlib/gzip header scan over first 2MB ===")
found=0
for off in range(0, min(len(l1),2<<20)):
    if l1[off]==0x78 and l1[off+1] in (0x01,0x5e,0x9c,0xda):
        try:
            o=zlib.decompressobj(15).decompress(l1[off:off+(1<<20)])
            if len(o)>64:
                print("   zlib @0x%x -> %d %r" % (off,len(o),o[:48])); found+=1
                if found>=5: break
        except Exception: pass
    if l1[off]==0x1f and l1[off+1]==0x8b:
        print("   gzip @0x%x" % off); found+=1
print("   found:", found)
