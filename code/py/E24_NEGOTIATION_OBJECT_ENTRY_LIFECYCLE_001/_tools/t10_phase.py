import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_tools")
from peh import *
img = Img()
OUT=open(r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_data\out_phase.txt","w",encoding="utf-8")
for rva,n,tag in [(0x6AA440,0x60,"phase=1 @6AA470"),
                  (0x6AB2A0,0x80,"phase=3 @6AB2ED"),
                  (0x6A12E0,0x150,"init/reset @6A1312/6A13F2"),
                  (0x6A1520,0x60,"phase=eax @6A1551"),
                  (0x6AA6C0,0x60,"phase=ebx @6AA6EB"),
                  (0x6A90C0,0x40,"0x6A90DF (cmp phase,3)"),
                  (0x6A9B10,0x50,"0x6A9B32 (cmp phase,3)"),
                  (0x6AAA50,0x60,"0x6AAA79 (cmp phase,3)")]:
    dump(img, rva, n, OUT, tag)
OUT.close()
print(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_data\out_phase.txt",encoding="utf-8").read())
