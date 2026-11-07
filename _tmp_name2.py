import struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetailBase.dll"
d = open(p,'rb').read()
# 名字表自 0x00B039CA 起，每项以 2 字节 hint 开头
sec_va, sec_raw = 0x00B02000, 0x00AF7C00
# 建立 名字RVAs 列表
start = 0x00AF7C00 + (0x00B039CA - 0x00B02000)
cur = start
names = []
while cur < 0x00AF7C00 + 0x4EBA:
    e = d.find(b'\0', cur)
    if e < 0 or e == cur: break
    raw = d[cur:e]
    hint = struct.unpack_from('<H', raw, 0)[0]
    names.append((cur - 0xAF7C00 + 0x00B02000, hint, raw[2:].decode('latin1')))
    cur = e + 1
print("名字总数 =", len(names))
# 目标项 (0x10B022F4 - 0x00B02000)/4 = 189
idx = (0x00B022F4 - 0x00B02000)//4
print("目标索引 =", idx)
for k in range(idx-2, idx+3):
    if 0 <= k < len(names):
        print("  [%d] RVA 0x%08X hint=%d  %r" % (k, names[k][0], names[k][1], names[k][2]))
