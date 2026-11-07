# -*- coding: utf-8 -*-
"""分析抓到的 8081 包结构，判定加密方式。

已知：每包 UDP 载荷 308 字节，加密，含重复 16 字节块。
检查：
  1. 长度是否 16 的倍数（AES 块对齐）
  2. 是否有可识别头部
  3. 重复块的位置与周期
  4. 包间差异（前 N 字节是否恒定 = 可能是 IV/头）
"""
import sys

# 从抓包结果里取前 3 个包
PKTS = [
    "53411cbfdbdae9b6596e6dccbb74a92a0dd046048243f1eeec0c6c44e1657c02b9f6ed342267c61e9aad5e80df737d9e82aac02dff618092e90e8cf0b0859cf711f538601aaadf5719a3d4137eaa6ef746bf19ca15ff3d444674cc01794260b34abd9dcea1348f41e0bcbede8650d4424abd9dcea1348f41e0bcbede8650d4424abd9dcea1348f41e0bcbede8650d4422043bd570880a7c9e874c57366e9fb714abd9dcea1348f41e0bcbede8650d4424abd9dcea1348f41e0bcbede8650d4424abd9dcea1348f41e0bcbede8650d4424abd9dcea1348f41e0bcbede8650d4424abd9dcea1348f41e0bcbede8650d4424abd9dcea1348f41e0bcbede8650d4424abd9dcea1348f41e0bcbede8650d442a2abfb2049e93d283ff825d8b7aaa463e1fdb2a7266c5b219c3ca365a0321bbd000067e2",
    "758f114da8b696adf7dcb28e2e634b577d1d65363709e7436bbec8ca5837c2315c3103275295782551873df765f10d0938ab434625d19778a0a7527e9663c2100afcf2caa37428dbea8e12e5b97923f2ce1cd7b4ad7c85eb7abf8e4b9aee8dc1e1ac6919b4f131f4dca213821aea42c8e1ac6919b4f131f4dca213821aea42c8e1ac6919b4f131f4dca213821aea42c859ee291da741a3d96f1ba0cb7d21bfc7e1ac6919b4f131f4dca213821aea42c8e1ac6919b4f131f4dca213821aea42c8e1ac6919b4f131f4dca213821aea42c8e1ac6919b4f131f4dca213821aea42c8e1ac6919b4f131f4dca213821aea42c8e1ac6919b4f131f4dca213821aea42c8e1ac6919b4f131f4dca213821aea42c832d345abe5343a838176c100f6e07fb19cb17a71fd79048978dd8c3cef2b0c160000641c",
    "e93dbabea80717691362f9f50d437fb22f75832a0c26c3b7f3cb8135ccca83aa0f8b9b283d6cf2f62f74a1002233e7695caac10476115c645a455c9af7bb879f4cd0b53e1975cd06bee2d23f5bc85cc0a99165fa72c8e0cb655a0a96e3a1d51239ae40e66fee58e519e23b20213cbc6239ae40e66fee58e519e23b20213cbc6239ae40e66fee58e519e23b20213cbc624f426188f958523554fd426365481ebe39ae40e66fee58e519e23b20213cbc6239ae40e66fee58e519e23b20213cbc6239ae40e66fee58e519e23b20213cbc6239ae40e66fee58e519e23b20213cbc6239ae40e66fee58e519e23b20213cbc6239ae40e66fee58e519e23b20213cbc6239ae40e66fee58e519e23b20213cbc627bc1746560a3e84e492b80053acbedc7be3e243f84842cf1c4550d26e34dff690000086e",
]


def main():
    datas = [bytes.fromhex(p) for p in PKTS]
    print("包数: %d" % len(datas))
    for i, d in enumerate(datas):
        print("  包%d: %d 字节, %%16=%d, %%8=%d" % (i, len(d), len(d) % 16, len(d) % 8))
    print()

    d0 = datas[0]
    print("=== 结构：按 16 字节分块 ===")
    for off in range(0, len(d0), 16):
        blk = d0[off:off + 16]
        print("  +%03d  %s" % (off, blk.hex(" ")))
    print()

    print("=== 重复块统计（包0）===")
    from collections import Counter
    blocks = [d0[i:i + 16] for i in range(0, len(d0) - 15, 16)]
    cnt = Counter(blocks)
    for blk, n in cnt.most_common(6):
        if n > 1:
            idx = [i for i, b in enumerate(blocks) if b == blk]
            print("  %s x%d  @块 %s" % (blk.hex(), n, idx))
    print()

    print("=== 包间差异：前 N 字节是否相同 ===")
    minlen = min(len(d) for d in datas)
    same = 0
    for i in range(minlen):
        if all(d[i] == datas[0][i] for d in datas):
            same += 1
        else:
            break
    print("  从开头连续相同的字节数: %d" % same)
    print("  包0 前 32: %s" % datas[0][:32].hex(" "))
    print("  包1 前 32: %s" % datas[1][:32].hex(" "))
    print("  包2 前 32: %s" % datas[2][:32].hex(" "))
    print()

    print("=== 尾部 8 字节（可能是校验/padding）===")
    for i, d in enumerate(datas):
        print("  包%d: %s" % (i, d[-8:].hex(" ")))
    print()

    print("=== 熵值（判断是否全密文）===")
    import math
    for i, d in enumerate(datas):
        freq = Counter(d)
        ent = -sum((c / len(d)) * math.log2(c / len(d)) for c in freq.values())
        print("  包%d: %.3f bits/byte (理论上限 8.0)" % (i, ent))


if __name__ == "__main__":
    main()
