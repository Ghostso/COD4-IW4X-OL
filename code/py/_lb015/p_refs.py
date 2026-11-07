import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_lb015")
import img

print("dword_refs(0xDC7270):", [hex(x) for x in img.dword_refs(0xDC7270)])
print("dword_refs(0xDC7274):", [hex(x) for x in img.dword_refs(0xDC7274)])
print()
print("dword_refs(0xDF96D8):", [hex(x) for x in img.dword_refs(0xDF96D8)][:20])
print()
print("call_rel32_hits(0x632680):", [hex(x) for x in img.call_rel32_hits(0x632680)])
print()
print("what is at 0xDF96D8:")
img.show(0xDF96D8, count=8)
print()
print("dwords at 0xDF96D8:", [hex(img.dword(0xDF96D8+4*i)) for i in range(10)])
print()
print("preceding vtable dwords (0xDC7240..0xDC7270):")
for va in range(0xDC7240, 0xDC7274, 4):
    print("  %08X = %08X" % (va, img.dword(va)))
