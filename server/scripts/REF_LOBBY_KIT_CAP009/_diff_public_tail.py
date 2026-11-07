# -*- coding: utf-8 -*-
"""看 public.result 里 blob 之后的额外 TLV(旧 33428 vs 裸档案 32768)。"""
import os
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.join(ROOT, "player_profiles", "public.result")


def main():
    pub = open(PUB, "rb").read()
    # 解析到 blob
    k = 0
    while k < len(pub):
        t = pub[k]
        if t == 0x0A:
            k += 9
        elif t == 0x08:
            k += 5
        elif t == 0x13:
            ln = struct.unpack_from("<I", pub, k + 2)[0]
            print("blob len=%d, blob 结束于 %d" % (ln, k + 6 + ln))
            rest = pub[k + 6 + ln:]
            print("blob 之后还有 %d 字节" % len(rest))
            print("尾部 hex: %s" % rest[:200].hex(" "))
            print()
            # 尝试解析尾部 TLV
            m = 0
            while m < len(rest):
                t2 = rest[m]
                if t2 == 0x0A:
                    v = struct.unpack_from("<Q", rest, m + 1)[0]
                    print("  0x0A u64 = %d" % v); m += 9
                elif t2 == 0x08:
                    v = struct.unpack_from("<I", rest, m + 1)[0]
                    print("  0x08 u32 = %d (0x%X)" % (v, v)); m += 5
                elif t2 == 0x10:
                    j = rest.find(b"\x00", m + 1)
                    print("  0x10 str = %r" % rest[m + 1:j]); m = j + 1
                elif t2 == 0x13:
                    ln2 = struct.unpack_from("<I", rest, m + 2)[0]
                    print("  0x13 blob len=%d" % ln2)
                    m += 6 + ln2
                elif t2 == 0x03:
                    print("  0x03 u8 = %d" % rest[m + 1]); m += 2
                else:
                    print("  ?tag 0x%02X @%d" % (t2, m))
                    break
            break
        else:
            print("?tag 0x%02X @%d" % (t, k))
            break
    return 0


if __name__ == "__main__":
    sys.exit(main())
