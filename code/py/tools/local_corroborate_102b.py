#!/usr/bin/env python3
"""本地佐证 (2):
(a) dump BD_MESSAGING_* 错误码族所在的 bd 错误注册块 —— 按服务顺序枚举，可作本地服务清单;
(b) dump eventlog 分类块 0x9E0B00-0x9E0C60 全文;
(c) 测 .tp3 代码节是否可读 x86 (取 0xA16000 附近看形态);
(d) 全镜像搜 length-prefixed AS3 串 'messaging' 独立出现处。
"""
import struct
E = r"E:\codol_re\client_image_20261027.bin"
data = open(E, "rb").read()
N = len(data)

def show(lo, hi, label=""):
    print("=== %s 0x%X-0x%X ===" % (label, lo, hi))
    for i in range(lo, hi, 16):
        c = data[i:i+16]
        print("  0x%08X  %-47s  %s" % (i, " ".join("%02x"%b for b in c),
              "".join(chr(b) if 32<=b<127 else "." for b in c)))
    print()

# (a) bd error block around 0x9E2200-0x9E2600
show(0x9E21C0, 0x9E2600, "bd error registry")

# (b) eventlog category block
show(0x9E0B00, 0x9E0C80, "eventlog categories")

# (c) code readability test
show(0xA16000, 0xA16100, "tp3 code head")

# (d) AS3 length-prefixed 'messaging' occurrences: pattern [len][messaging]
print("=== length-prefixed AS3 'messaging' ===")
needle = b"\x09messaging"   # len=9
i=0; hits=[]
while True:
    p = data.find(needle, i)
    if p<0: break
    hits.append(p); i=p+1
print("len-prefixed 0x09+'messaging' hits:", ["0x%X"%h for h in hits[:20]], "total", len(hits))
for p in hits[:10]:
    show(p-16, p+24, "ctx 0x%X"%p)
