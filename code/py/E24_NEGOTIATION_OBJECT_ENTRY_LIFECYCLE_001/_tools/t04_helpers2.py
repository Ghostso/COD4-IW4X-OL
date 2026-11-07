import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_tools")
from peh import *
img = Img()
OUT=open(r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_data\out_helpers2.txt","w",encoding="utf-8")
# (VA, nbytes, tag) -- convert VA->RVA
for va,n,tag in [(0xAAA230,0x140,"VA 0xAAA230 (post-negotiate)"),
                 (0xACE180,0x70,"VA 0xACE180 (16-byte check A)"),
                 (0xACE1B0,0x50,"VA 0xACE1B0 (commit A)"),
                 (0xACE080,0x60,"VA 0xACE080 (16-byte check B)"),
                 (0xACE040,0x50,"VA 0xACE040"),
                 (0xACDFB0,0x50,"VA 0xACDFB0 (err->str)")]:
    dump(img, va-img.IB, n, OUT, tag)
# dispatcher tail 0x6AC2D0..0x6AC3D0
dump(img, 0x6AC2D0, 0x110, OUT, "DISPATCHER TAIL 0x6AC2D0")
OUT.close()
print(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_data\out_helpers2.txt",encoding="utf-8").read())
