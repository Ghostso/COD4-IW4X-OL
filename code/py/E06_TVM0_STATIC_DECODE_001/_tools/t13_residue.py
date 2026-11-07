import collections, math
p=r"D:\BaiduNetdiskDownload\使命召唤OL\E06_TVM0_STATIC_DECODE_001\_work\depacked_tvm0.bin"
d=open(p,"rb").read()
def ent(b):
    if not b: return 0.0
    c=collections.Counter(b); n=len(b)
    return -sum((v/n)*math.log2(v/n) for v in c.values())
print("=== residue-class entropy test (XOR-with-repeating-key detector) ===")
print("value      period1 ... period8   (low = sharp/structured, high = random)")
for period in range(1,9):
    ents=[]
    for r in range(period):
        ents.append(ent(d[r::period][:200000]))
    if period==1:
        print("period=%d  entropy=%.4f" % (period,ents[0]))
    else:
        print("period=%d  per-residue entropy: %s  (min=%.3f max=%.3f)" % (
            period, " ".join("%.3f"%e for e in ents), min(ents), max(ents)))
print()
print("=== plaintext if single-byte XOR key: most frequent byte per period-8 residue ===")
for r in range(8):
    c=collections.Counter(d[r::8])
    print("  residue %d: top=%s" % (r, ["0x%02X:%d"%(k,v) for k,v in c.most_common(3)]))
print()
print("=== does depacked .tvm0 contain an AP32 header (nested)? ===")
print("  AP32 count in depacked .tvm0:", d.count(b"AP32"))
print("=== does depacked .tvm0 contain a PE header (MZ/PE)? ===")
print("  MZ at 0:", d[:2]==b"MZ", " PE sig occurrences:", d.count(b"PE\x00\x00"))