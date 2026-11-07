#!/usr/bin/env python3
"""nQloP0oCVWR6RDJS 编码分析 + 31902622 与 titleId/zoneId 关系 + base64 解码。"""
import base64, struct, binascii
V=31902622
s="nQloP0oCVWR6RDJS"
print("nQlo =", s, "len", len(s))
# base64 decode
for pad in ["","=","=="]:
    try:
        b=base64.b64decode(s+pad)
        print("  b64 decode(%r): %s  hex=%s" % (s+pad, b, b.hex()))
    except Exception as e:
        print("  b64 %r fail: %s"%(pad,e))

# 是否是 hex? 含非hex字符 nQlo... -> 否
# 32 进制/自定义?
# 试作为 16 字节直接解释
raw=s.encode()
print("\nraw bytes:", raw.hex())
print("as 4 u32 LE:", [struct.unpack_from("<I",raw,i)[0] for i in range(0,16,4)])
print("as 2 u64 LE:", [struct.unpack_from("<Q",raw,i)[0] for i in range(0,16,8)])

# 31902622 关系
print("\n=== 31902622 vs titleId/zoneId ===")
for name,v in [("titleId",1004),("zoneId",83886082),("build",1649370),
               ("stnd_zone",83886082)]:
    print("  V - %s = %d ; V / %s = %.4f"%(name,V-v,name,V/v if v else 0))
print("  V & 0xFFFF =", V&0xffff, " V>>16 =", V>>16)
print("  V = 0x%X" % V)

# 31902622 的 base64?
print("\n31902622 hex bytes:", V.to_bytes(4,'little'))
print("  b64 of LE bytes:", base64.b64encode(V.to_bytes(4,'little')))
print("  b64 of BE bytes:", base64.b64encode(V.to_bytes(4,'big')))

# 是否是 nQlo 的某种 32位折叠
import functools
raw32=[struct.unpack_from("<I",raw,i)[0] for i in range(0,16,4)]
print("\nnQlo 4 u32:", [hex(x) for x in raw32])
print("  XOR all:", hex(functools.reduce(lambda a,b:a^b, raw32)))
print("  ADD all & 0xffffffff:", hex(sum(raw32)&0xffffffff))
