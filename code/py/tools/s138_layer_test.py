#!/usr/bin/env python3
"""138 · 关键判定：11/4 的 blob 内层，能否作为 dwRoomMessage 位流被 0x634870 解析？

判据（0x634870）:
   readBits(3) 必须 == 3         (0x6348AE push 3; call 0xB774E0 —— 断言相等!)
   readBits(8) = type, 必须 <= 0x2E (0x63494A cmp eax,0x2e / ja)
若两者都成立，说明"11/4 的 blob 就是 dwRoomMessage 位流容器"。
"""
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SAMPLES = [
    ("11/4 #61 room族 141B", "0x02"),
    ("11/4 #62 ready族 17B", "0x18"),
]


class BitReader(object):
    def __init__(self, data):
        self.d = data
        self.pos = 0

    def read(self, n):
        if self.pos + n > len(self.d) * 8:
            return None
        v = 0
        for i in range(n):
            p = self.pos + i
            v = (v << 1) | ((self.d[p >> 3] >> (7 - (p & 7))) & 1)
        self.pos += n
        return v


def probe(name, data):
    br = BitReader(data)
    tag = br.read(3)
    typ = br.read(8)
    print("%-26s 首3位=%s 首8位(类型)=%s" % (
        name,
        ("%d(%s)" % (tag, "==3 ✓" if tag == 3 else "≠3 ✗")) if tag is not None else "?",
        ("0x%02X(%s)" % (typ, "<=0x2E ✓" if typ is not None and typ <= 0x2E else "越界 ✗"))
        if typ is not None else "?"))
    return tag == 3 and typ is not None and typ <= 0x2E


if __name__ == "__main__":
    print("=== 判定：blob 内层能否直接当 dwRoomMessage 位流 ===")
    print("（判据：readBits(3)==3 且 readBits(8)<=0x2E）\n")
    for n, b in SAMPLES:
        print("  %s 首字节=0x%02X" % (n, int(b, 16)))
    print()
    print("  → room族首字节 0x02 = 00000010 : 首3位=000=0 ✗ 不等于3")
    print("  → ready族首字节 0x18 = 00011000 : 首3位=000=0 ✗ 不等于3")
    print()
    print("★ 结论：11/4 的 blob 内容【不是】dwRoomMessage 位流。")
    print("  层2(room/ready族) 与 层3(3位tag+8位type) 是两套不同数据。")
    print()
    print("=== 那么 dwRoomMessage 位流在哪个容器里？===")
    print("  候选 A: 11/4 报文里 blob 之后的 08 <u32 1> 段（不是 blob）")
    print("  候选 B: 另一个 service/task 的报文（非 11/4）")
    print("  候选 C: 0x6371F0 收到的 blob#2（6/5 opcode=6 的内层）")
    print("  ⇒ 需用 0x637000 的实际入参在活进程里确认（或继续静态追 0x6370A1）")
