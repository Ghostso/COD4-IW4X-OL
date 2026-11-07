import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_lb015")
import img
for g in (0x82E13FC, 0x82E1400, 0x82E1404, 0x849B61C, 0x82E140C, 0x333ABDC, 0x76446B0):
    r = img.dword_refs(g)
    print("%08X refs(%d): %s" % (g, len(r), [hex(x) for x in r]))
