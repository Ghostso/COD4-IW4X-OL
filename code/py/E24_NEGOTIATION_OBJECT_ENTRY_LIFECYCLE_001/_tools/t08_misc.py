import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_tools")
from peh import *
img = Img()
OUT=open(r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_data\out_misc.txt","w",encoding="utf-8")
for rva,n,tag in [(0x74FF60,0x70,"0xB4FF60 (helper of ACE180)"),
                  (0x687C30,0xC0,"0xA87C30 slot+1 full"),
                  (0x687D50,0x60,"0xA87D50 slot+3 full"),
                  (0x41DDC0,0xA0,"0x41DE91 context (other 5F4 reader)"),
                  (0x6A85B50,0x60,"0xA85B50"),
                  (0x6A85640-0x100,0x40,"pre 0xA85640")]:
    dump(img, rva, n, OUT, tag)
OUT.close()
print(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_data\out_misc.txt",encoding="utf-8").read())
