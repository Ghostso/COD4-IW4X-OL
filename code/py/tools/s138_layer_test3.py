#!/usr/bin/env python3
"""138 · 修正后的分层：0x637000 = read5(断言3) + read8 → 直通 0x634870(read3 + read8)。

注意：0x634870 是从**新的位流读取器**开始读（直通路径里 [edx+0x25C8] 是 room，
但位流读取器仍是同一个 esi）。所以 3位tag 紧跟在那 8 位之后。
"""
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


class BR(object):
    def __init__(self, d):
        self.d = d
        self.p = 0

    def r(self, n):
        if self.p + n > len(self.d) * 8:
            return None
        v = 0
        for i in range(n):
            q = self.p + i
            v = (v << 1) | ((self.d[q >> 3] >> (7 - (q & 7))) & 1)
        self.p += n
        return v

    def left(self):
        return len(self.d) * 8 - self.p


SAMPLES = [
    ("11/4 #62 ready(17B)", "181c5a98d6145391cf0114da0000000000"),
    ("11/4 #61 room(141B,前32B)",
     "020400000030000000e068ab5bab63ab030000000098030000f0304706d006f745963647279736460"),
    ("11/4 #63 room(11B)", "02020000000800000080080001000000"),
    ("11/4 #13 type1(146B,前32B)",
     "0a88776655443322111308"),
]

if __name__ == "__main__":
    for name, hx in SAMPLES:
        try:
            d = bytes.fromhex(hx)
        except ValueError:
            print("%s : hex 无效" % name)
            continue
        br = BR(d)
        c5 = br.r(5)
        v8 = br.r(8)
        print("=" * 70)
        print("%s (%d 字节)" % (name, len(d)))
        print("   raw 前16B: %s" % d[:16].hex())
        print("   [0x637000] 5位code = %s   %s" % (c5, "✓==3" if c5 == 3 else "✗!=3"))
        if c5 != 3:
            print("   → 0x637000 直接返回失败")
            print()
            continue
        print("   [0x637000] 8位     = %s   %s" % (
            v8, "→ Manifold(0x6256C0)" if v8 == 1 else "→ 直通 0x634870"))
        if v8 != 1:
            t3 = br.r(3)
            typ = br.r(8)
            ok3 = (t3 == 3)
            okT = (typ is not None and typ <= 0x2E)
            print("   [0x634870] 3位tag  = %s   %s" % (t3, "✓==3" if ok3 else "✗!=3"))
            print("   [0x634870] 8位type = %s   %s" % (
                typ, "✓<=0x2E" if okT else "✗越界"))
            if ok3 and okT:
                print("   ★★★ 完全通过！type=0x%02X" % typ)
        print()
