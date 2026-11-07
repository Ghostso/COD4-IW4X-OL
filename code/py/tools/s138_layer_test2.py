#!/usr/bin/env python3
"""138 · 用 0x637000 的正确判据重测 11/4 blob。

0x637000 分层：
  1) push 3 ; call 0xB779A0  建位流(buf, len*8)
  2) push 3 ; call 0xB774E0  读 **5 位** code（断言 ==3）
  3) push 8 ; call 0xB772E0  读 8 位 → [ebp-1]
  4) cmp [ebp-1], 1
       ==1 → Manifold（0x6256C0）
       !=1 → 直通 0x634870
  5) 0x634870 内部再读 3 位 tag + 8 位 type
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


SAMPLES = [
    ("11/4 #62 ready族(17B)", "181c5a98d6145391cf0114da0000000000"),
    ("11/4 #63 room族(11B)", "02020000000800000080080001000000"),
]

if __name__ == "__main__":
    print("=== 用 0x637000 的 5位+8位 判据测 11/4 blob ===\n")
    for name, hx in SAMPLES:
        d = bytes.fromhex(hx)
        br = BR(d)
        code5 = br.r(5)
        v8 = br.r(8)
        print("%s" % name)
        print("   raw     : %s" % d.hex())
        print("   首5位   : %s (0x637000 要求==3 %s)"
              % (code5, "✓" if code5 == 3 else "✗"))
        print("   次8位   : %s (==1 则走 Manifold)" % v8)
        if code5 == 3 and v8 != 1:
            tag3 = br.r(3)
            typ = br.r(8)
            print("   直通路: tag3=%s (0x634870 要求==3 %s), type=%s"
                  % (tag3, "✓" if tag3 == 3 else "✗", typ))
        print()

    print("=== 手算对照 ===")
    d = bytes.fromhex("181c5a98d6145391cf0114da0000000000")
    bits = "".join(format(b, "08b") for b in d[:3])
    print("  ready族前3字节 = %s" % bits)
    print("                   首5位=%s  次8位=%s" % (bits[:5], bits[5:13]))
    d2 = bytes.fromhex("02020000000800000080080001000000")
    bits2 = "".join(format(b, "08b") for b in d2[:3])
    print("  room族 前3字节 = %s" % bits2)
    print("                   首5位=%s  次8位=%s" % (bits2[:5], bits2[5:13]))
