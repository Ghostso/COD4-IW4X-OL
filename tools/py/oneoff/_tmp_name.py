import struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetailBase.dll"
d = open(p,'rb').read()
sec_va, sec_raw = 0x00B02000, 0x00AF7C00
def s(rva, n=64):
    o = sec_raw + (rva - sec_va)
    e = d.index(b'\0', o)
    return d[o:e].decode('latin1')
for rva in (0x00B04884, 0x00B04890, 0x00B048A2, 0x00B048B8):
    print("0x%08X -> %r" % (rva, s(rva)))
print()
pat = struct.pack('<I', 0x10B022F4)
hits = []
i = 0
while True:
    i = d.find(pat, i)
    if i < 0: break
    hits.append(i); i += 1
print("引用 0x10B022F4 的位置 (%d 处):" % len(hits))
for h in hits[:20]: print("  文件偏移 0x%X" % h)
# .text raw 0x400 VA 0x1000
print()
print("=== 补丁点 文件偏移 0x27D80C 对应 VA 0x%X ===" % (0x27D80C - 0x400 + 0x1000))
