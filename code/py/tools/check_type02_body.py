"""核对: 客户端上行的 type 0x02 body, 是否符合 dwRoomMessageText 的 serialize 格式。

Text.serialize = 0x625970, deserialize = 0x625a20。

客户端上行 0x02 body 实测(87 条里 53 条):
    020200000008000000800800
    020200000018000000d0000000000000
    020600000030000000e068ab5bab63ab03...
    020400000028000000b8180000...

若 0x02 是 Text, body 应是位流: readBits(3)+readData(8)=0x02...
但实测 body 以 `02 02 ...` 开头 —— 若按位流读:
    前 5 位 = 0x02 = 2, 不等于 3!  -> 不是位流

所以 0x02 上行的 body 不是 Text.serialize 的输出。
需要确认: 0x634870 的 readData(8)=type 读到的 0x02, 和 body 首字节 0x02 是否同一个。

★ 关键: 0x634870 是**先读位流 type**, 再按 type 分派;
   分派后各 handler 继续读同一个位流。
   所以 body 的首字节确实是被 readData(8) 消费掉的 type。
   剩下的字节才是 handler 读的内容。

验证: 把 `0202000000180000...` 按位流读
    readBits(3) -> 应==3
若首字节是 0x02 (二进制 00000010), LSB-first 前 5 位 = 0b00010 = 2 ≠ 3。
矛盾! 说明 0x02 不是走这条路。

替代解释: 0x634870 的调用方(0x6371F0) 可能已经把 type 剥掉了。
"""
import struct


def bits(data, pos, n):
    v = 0
    for k in range(n):
        p = pos + k
        b, i = p // 8, p % 8
        if b >= len(data):
            return None
        if (data[b] >> i) & 1:
            v |= 1 << k
    return v


samples = [
    bytes.fromhex('020200000008000000800800'),
    bytes.fromhex('020200000018000000d0000000000000'),
    bytes.fromhex('020400000018000000a808000000003000000050110000000000'),
    bytes.fromhex('020600000030000000e068ab5bab63ab0300000000500000'),
]

print('=== 把 0x02 类 body 按位流读前 13 位 ===')
for s in samples:
    tag = bits(s, 0, 5)
    typ = bits(s, 5, 8)
    print('  %-42s readBits=%d readData=0x%02X' % (s.hex()[:40], tag, typ))
print()
print('结论: 首字节 0x02, LSB-first 前 5 位 = 2, 不等于 3 -> 不是位流头')
print()
print('=== 若把首字节剥掉, 从第 1 字节开始按位流读 ===')
for s in samples:
    tag = bits(s, 8, 5)
    typ = bits(s, 13, 8)
    print('  %-42s readBits=%d readData=0x%02X' % (s.hex()[:40], tag, typ))
