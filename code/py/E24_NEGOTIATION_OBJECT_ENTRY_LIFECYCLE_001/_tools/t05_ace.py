import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_tools")
from peh import *
img = Img()
OUT=open(r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_data\out_ace180.txt","w",encoding="utf-8")
dump(img, 0x6AC180-0x400000, 0x120, OUT, "VA 0xACE180 full")
dump(img, 0x6AC1B0-0x400000, 0x1A0, OUT, "VA 0xACE1B0 full")
# buffer source in 6AAE70: search where -0x210 / -0x220 written
dump(img, 0x6AAE70-0x400000, 0x2E0, OUT, "0x6AAE70 (VA 0xAAAE70)")
OUT.close()
print(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_data\out_ace180.txt",encoding="utf-8").read())
