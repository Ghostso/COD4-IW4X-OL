import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_lb015")
import img

def dump(vt, n=96):
    print("vtable @ %08X" % vt)
    for i in range(n):
        v = img.dword(vt + 4*i)
        tag = ""
        if 0x401000 <= v < 0xE65000: tag = "code"
        elif v == 0: tag = "null"
        print("   +0x%03X  %08X  %s" % (4*i, v, tag))
        if i>4 and v==0:
            pass

print("### around 0xDC7270")
dump(0xDC7270, 90)
