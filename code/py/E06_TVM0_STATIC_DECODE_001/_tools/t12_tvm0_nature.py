import math, collections, struct, hashlib
p=r"D:\BaiduNetdiskDownload\使命召唤OL\E06_TVM0_STATIC_DECODE_001\_work\depacked_tvm0.bin"
d=open(p,"rb").read()
print("=== .tvm0 depacked content: 0x%X (%d) bytes ===" % (len(d),len(d)))
def ent(b):
    if not b: return 0.0
    c=collections.Counter(b); n=len(b)
    return -sum((v/n)*math.log2(v/n) for v in c.values())
print("global entropy: %.4f bits/byte" % ent(d))
# per 64KB entropy
print("\nper-64KB entropy (first 20 blocks):")
for i in range(0,min(len(d),20*65536),65536):
    e=ent(d[i:i+65536])
    print("  0x%06X: %.4f" % (i,e))
# unigram
c=collections.Counter(d)
print("\ntop 12 byte values:", c.most_common(12))
print("zero bytes: %.2f%%" % (100.0*c[0]/len(d)))
print("0xCC bytes: %.2f%%" % (100.0*c[0xCC]/len(d)))
# look for ACSII strings
import re
strs=re.findall(rb"[\x20-\x7e]{6,}", d)
print("\nASCII strings (>=6): %d ; sample:" % len(strs))
for s in strs[:25]: print("   ", s[:90])