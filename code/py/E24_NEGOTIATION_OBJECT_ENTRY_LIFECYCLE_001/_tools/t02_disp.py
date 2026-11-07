import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_tools")
from peh import *
img = Img()
OUT=open(r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_data\out_6ac0c0_dispatch.txt","w",encoding="utf-8")
dump(img, 0x6AC0C0, 0x310, OUT, "DISPATCHER 0x6AC0C0")
OUT.close()
print(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_data\out_6ac0c0_dispatch.txt",encoding="utf-8").read())
