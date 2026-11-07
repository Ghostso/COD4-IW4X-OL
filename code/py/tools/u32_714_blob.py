#!/usr/bin/env python3
"""71/4 的 16 字节 blob 是否 base64；解码结果；31902622 的位结构。"""
import base64
import binascii

b0 = b"nQloP0oCVWR6RDJS"
b1 = b"++++++++++++++++"

for name, s in [("blob0", b0), ("blob1", b1)]:
    print("== %s = %r (len=%d) ==" % (name, s, len(s)))
    try:
        d = base64.b64decode(s)
        print("   base64 -> %s (len=%d)" % (d.hex(), len(d)))
        print("   as u64le = 0x%X" % int.from_bytes(d[:8], "little"))
        print("   as u64be = 0x%X" % int.from_bytes(d[:8], "big"))
    except Exception as e:
        print("   base64 err:", e)

print("\n31902622 = 0x%08X" % 31902622)
v = 31902622
print("  bits:", format(v, "032b"))
print("  low16=%d high16=%d" % (v & 0xFFFF, v >> 16))
print("  b0=0x%02X b1=0x%02X b2=0x%02X b3=0x%02X" % (v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF, (v >> 24) & 0xFF))

# 是否 = 某个日期(2000 epoch) / 序号
import datetime
for base_year, base in [(2000, 946684800), (1970, 0), (2010, 1262304000)]:
    print("  as unix ts (if =seconds since %d): %s" % (base_year, datetime.datetime.utcfromtimestamp(v + base) if v < 3e9 else "n/a"))

# 31902622 的十进制是否像 MAC 段拼接
print("\n  decimal digits:", str(v))
print("  split 319 026 22 :", "319.026.22")
print("  0x01E6CB9E 拆 01E6 CB9E")
