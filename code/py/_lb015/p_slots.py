import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_lb015")
import img
for a,n in ((0x62DE80,30),(0x62FDE0,20),(0x62C580,40),(0x62CD10,20),(0x62CD30,20),(0x62DE90,30),(0x62FDC0,20),(0x62FE30,20)):
    print("=== %08X ===" % a)
    img.show(a, count=n)
    print()
