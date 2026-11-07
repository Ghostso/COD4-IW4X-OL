import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_tools")
from peh import *
img = Img()
OUT=open(r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_data\out_key_funcs.txt","w",encoding="utf-8")
# (RVA, nbytes, tag) -- RVA is authoritative
items=[(0x6CE180,0x90,"checkA: VA 0xACE180 slot+3 first callee"),
       (0x6CE1B0,0x150,"commitA: VA 0xACE1B0 slot+3 second callee"),
       (0x6CE080,0x70,"checkB: VA 0xACE080 slot+2 first callee"),
       (0x6AA770,0x50,"0x6AA770 fail->state4"),
       (0x6AA230,0x100,"0x6AA230 post-negotiate"),
       (0x687BA0,0x80,"0x687BA0 ctor"),
       (0x687DB0,0x50,"0x687DB0 slot+0"),
       (0x687C30,0xA0,"0x687C30 slot+1"),
       (0x687CF0,0x60,"0x687CF0 slot+2"),
       (0x687D50,0x60,"0x687D50 slot+3")]
for rva,n,tag in items:
    dump(img, rva, n, OUT, tag)
OUT.close()
txt=open(r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_data\out_key_funcs.txt",encoding="utf-8").read()
print(txt)
