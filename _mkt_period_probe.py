# -*- coding: utf-8 -*-
"""深挖 common_marketplace_lite.ff 层二是否 4096 周期的重复密钥流。

初步: dist=0x1000 的 4KB 窗口 XOR 熵 = 7.41, 明显低于随机期望(~7.95)。
本脚本用大样本 + 多周期扫描确认是否为真实周期性。
"""
import math
import os
from collections import Counter

BODY = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "_cleanout", "mkt",
                    "common_marketplace_lite.ff.layer1.bin")


def ent(d):
    c = Counter(d)
    n = len(d)
    return -sum(v / n * math.log2(v / n) for v in c.values())


def random_expected_ent(n):
    """随机数据在 n 字节样本上的经验熵期望(256 符号)。"""
    if n <= 1:
        return 0.0
    return 8.0 - 255.0 / (2.0 * n * math.log(2))


def main():
    b = open(BODY, "rb").read()
    body = b[0x160:]            # 主体起点(层一 zone 名之后)
    print("body len", len(body))

    print("\n[A] 固定周期扫描: 用 64KB 样本 XOR, 看是否显著低于随机期望")
    n = 65536
    exp = random_expected_ent(n)
    print("    随机期望熵(64KB) = %.4f" % exp)
    rows = []
    for P in range(256, 8193, 64):
        if P + n > len(body):
            break
        x = bytes(a ^ c for a, c in zip(body[:n], body[P:P + n]))
        rows.append((ent(x), P))
    rows.sort()
    print("    最像周期的 8 个:")
    for e, P in rows[:8]:
        print("       P=%-6d xor-entropy=%.4f  (delta %+.4f)" % (P, e, e - exp))

    print("\n[B] 0x1000 周期的长样本验证(1MB)")
    P = 0x1000
    n2 = 1 << 20
    if P + n2 <= len(body):
        x = bytes(a ^ c for a, c in zip(body[:n2], body[P:P + n2]))
        print("    1MB XOR@0x1000 entropy=%.4f  随机期望=%.4f"
              % (ent(x), random_expected_ent(n2)))

    print("\n[C] 分块统计: 每 4096 字节块的字节直方图是否异常一致")
    blk = 4096
    entropies = []
    for i in range(0, min(len(body), 4096 * 32), blk):
        entropies.append(ent(body[i:i + blk]))
    print("    前 32 个 4KB 块熵: min=%.3f max=%.3f avg=%.3f"
          % (min(entropies), max(entropies), sum(entropies) / len(entropies)))


if __name__ == "__main__":
    main()
