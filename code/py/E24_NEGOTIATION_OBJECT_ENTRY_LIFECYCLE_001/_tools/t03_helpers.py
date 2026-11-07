import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_tools")
from peh import *
img = Img()
OUT=open(r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_data\out_helpers.txt","w",encoding="utf-8")
for rva,n,tag in [(0x6AAA30,0x120,"0xAAA230 (post-negotiate call)"),
                  (0x6AA770,0x110,"0xAAA770 (fail->state4)"),
                  (0x687BA0,0x80,"0xA87BA0 (ctor of 5F4 obj)"),
                  (0x687C30,0x60,"0xA87C30 (vtable slot+1)"),
                  (0x687CF0,0x60,"0xA87CF0 (vtable slot+2)"),
                  (0x687D50,0x60,"0xA87D50 (vtable slot+3)"),
                  (0x6ACE180,0x60,"0xACE180"),
                  (0x6ACE1B0,0x40,"0xACE1B0")]:
    dump(img, rva, n, OUT, tag)
OUT.close()
print(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_data\out_helpers.txt",encoding="utf-8").read())
