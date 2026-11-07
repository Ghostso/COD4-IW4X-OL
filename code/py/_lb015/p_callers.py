import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_lb015")
import img
for t in (0x62C000, 0x632680, 0x632A00, 0x62FD90, 0x62FDE0):
    print("call_rel32 -> %08X :" % t, [hex(x) for x in img.call_rel32_hits(t)])
print()
print("dword_refs(0x62C000):", [hex(x) for x in img.dword_refs(0x62C000)])
print()
# who references the vtable slot addresses (i.e., vcall sites)
print("=== look for the region where the ctor is called ===")
img.show(0x62C000, count=1)
