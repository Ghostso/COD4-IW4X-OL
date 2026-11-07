"""决定性验证: 把客户端真实上行 body 按 0x634870 的读法逐字节走一遍。

0x634870 读法:
    bit  0..4   readBits(3)   必须 == 3   (5 位, LSB-first)
    bit  5..12  readData(8)   得到 type
    之后 handler 继续从 bit 13 读

真实上行 body（完整 = L2 里 13 08 <len> 之后的内容）:
    以 0x3AC62E5D 那次为例, 我们从 lobby 日志拿到的 body 是
    已经剥掉 L2 封装的 —— 即 `02 04 00 00 00 30 ...`

若按上面的读法:
    首字节 0x02 = 0b00000010
    LSB-first 前 5 位 = 00010b = 2  ≠ 3    -> 位流头不成立

⇒ 客户端上行**根本不经过 0x634870 的位流读取**。

那么客户端上行到底走哪条路?
    0x637000 里 readBits(3)+readData(8) 得到的是 0x02,
    然后 `cmp eax, 1 ; jne 0x63718D` —— 不等于 1 就走 0x63718D 分支,
    该分支直接 call 0x634870。

    但 0x634870 **自己又读一遍** readBits(3)+readData(8)。
    若流游标已被 0x637000 前移 13 位, 那 0x634870 读到的是
    body 的第 2 个字节起 —— 这就解释了 readBits=2 的怪现象!

验证: 若游标在 bit 13, 从那里按 LSB-first 读 5 位应 == 3。
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
    ('16B', '020200000018000000d0000000000000'),
    ('12B', '020200000008000000800800'),
    ('26B', '020400000018000000a808000000003000000050110000000000'),
    ('59B', '020600000030000000e068ab5bab63ab030000000050000000703100000000000000003001000080220000000020000000c0a185694d3115f91c00'),
    ('17B', '181c5a98d6145391cf01acb50100000000'),
]

print('=== 从 bit 0 读 ===')
for name, h in samples:
    b = bytes.fromhex(h)
    print('  %-4s readBits=%d readData=0x%02X'
          % (name, bits(b, 0, 5), bits(b, 5, 8)))

print()
print('=== 从 bit 8 (跳过第 1 字节) 读 ===')
for name, h in samples:
    b = bytes.fromhex(h)
    print('  %-4s readBits=%d readData=0x%02X'
          % (name, bits(b, 8, 5), bits(b, 13, 8)))

print()
print('=== 从 bit 13 读 (假设游标已被前移) ===')
for name, h in samples:
    b = bytes.fromhex(h)
    print('  %-4s readBits=%d readData=0x%02X'
          % (name, bits(b, 13, 5), bits(b, 18, 8)))

print()
print('=== 若把首字节当外层 type, 从 byte1 起找位流头 ===')
for name, h in samples:
    b = bytes.fromhex(h)
    hit = None
    for bit in range(8, min(len(b) * 8 - 13, 200)):
        if bits(b, bit, 5) == 3:
            t = bits(b, bit + 5, 8)
            if t is not None and t in {0x02, 0x0F, 0x17, 0x1D, 0x10, 0x11}:
                hit = (bit, t)
                break
    print('  %-4s %s' % (name, ('★ bit %d type=0x%02X' % hit) if hit else '无'))
