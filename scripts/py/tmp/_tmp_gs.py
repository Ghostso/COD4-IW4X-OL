import sys, struct
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
g = bytes.fromhex(
 "0A011000000000000013088500000081"
 "0000000204000000A4010000181802000000"
 "467D09D8AF02F807F8070000F807F807"
 "0000F807F8070000F807F8070000F807"
 "F8070000F807F8070000F807F8070000"
 "F807F8070000F807F8070000F807F807"
 "00E84BFA9A138B1740000000187A237A"
 "72634B73830000001848107828384800"
 "08485020304068580050000000706100"
 "00000000000000000000080100000000")
print("总长", len(g))
print("0-17 :", g[:18].hex(" "))
print("  0A + u64 =", struct.unpack_from("<Q", g, 1)[0])
print("  13 08 + u32 =", struct.unpack_from("<I", g, 11)[0])
inner_len = struct.unpack_from("<I", g, 15)[0]
print("  u32 inner_len =", inner_len, " (18+%d=%d, 剩 %d)" % (inner_len, 18+inner_len, len(g)-18))
inner = g[18:18+inner_len]
print()
print("inner(%d):" % len(inner), inner.hex(" "))
print()
# 逐字节找 F807 对
import re
print("F807 出现次数:", inner.count(b"\x07\xf8"))
print("尾部 24B:", g[-24:].hex(" "))
