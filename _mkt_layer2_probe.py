# -*- coding: utf-8 -*-
"""common_marketplace_lite.ff 层二探索(只读)。

层一已知: AES-192-CTR(key=da135e91..., iv=文件内 40B payload 的 [24:40])
          -> 'IWffs100' + 0 + 288B(高熵) + zoneName@0x12C + 主体(高熵)

本脚本检验几类假设:
  1) 周期性 —— 若为重复 XOR 密钥流, 则 data[i]^data[i+P] 的熵会显著下降;
  2) 基于 zone 名的密钥派生(sha256/md5) + AES-CTR;
  3) 主体是否只是"结构化数据 XOR 低熵流"(看相差窗口的熵)。
"""
import hashlib
import math
import os
import struct
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "CODOLServer", "_mainline"))

BODY = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "_cleanout", "mkt",
                    "common_marketplace_lite.ff.layer1.bin")


def ent(d):
    if not d:
        return 0.0
    c = Counter(d)
    n = len(d)
    return -sum(v / n * math.log2(v / n) for v in c.values())


def main():
    b = open(BODY, "rb").read()
    print("size", len(b))
    print("total entropy %.3f" % ent(b))

    zone = b"common_marketplace_lite"
    # 主体起点: zone 名 + NUL 填充到 0x160? 先看 0x160 起
    body_off = 0x160
    body = b[body_off:]
    print("body@0x%X len=%d entropy=%.3f" % (body_off, len(body), ent(body)))

    # ---- 1) 周期性 ----
    print("\n[1] 周期性检验 (body 前 256KB, 取差窗口熵; 接近 8.0 = 无周期)")
    sample = body[:262144]
    best = []
    for P in (16, 32, 64, 128, 256, 512, 1024, 2048, 4096):
        if P >= len(sample):
            continue
        x = bytes(a ^ c for a, c in zip(sample[:65536], sample[P:P + 65536]))
        e = ent(x)
        best.append((e, P))
        print("   P=%-5d xor-entropy=%.4f" % (P, e))
    best.sort()
    print("   最小熵周期:", best[0])

    # ---- 2) 基于 zone 名的密钥派生尝试 ----
    print("\n[2] zone 名派生密钥 + AES-CTR (看是否能出 'IWff' / 可见串)")
    try:
        from Crypto.Cipher import AES
        for name, key in [
            ("sha256(zone)[:16]", hashlib.sha256(zone).digest()[:16]),
            ("sha256(zone)[:24]", hashlib.sha256(zone).digest()[:24]),
            ("md5(zone)", hashlib.md5(zone).digest()),
            ("sha256(zone*2)[:16]", hashlib.sha256(zone * 2).digest()[:16]),
        ]:
            for ivdesc, iv in [
                ("zeros", b"\x00" * 16),
                ("md5(zone)[:16]", hashlib.md5(zone).digest()),
                ("sha256(zone)[:16]", hashlib.sha256(zone).digest()[:16]),
            ]:
                for keylen, kk in ((16, key[:16]), (24, (key + b"\x00" * 24)[:24])):
                    try:
                        out = AES.new(kk, AES.MODE_CTR,
                                      nonce=b"",
                                      initial_value=iv).decrypt(body[:4096])
                        e = ent(out)
                        if e < 7.0 or b"IWff" in out:
                            print("   HIT %s / %s / key%d ent=%.3f %r"
                                  % (name, ivdesc, keylen * 8, e, out[:24]))
                    except Exception as e:
                        pass
        print("   (无 HIT 即该假设不成立)")
    except ImportError:
        print("   pycryptodome 不可用")

    # ---- 3) 主体窗口互差(看是否为同一密钥流不同段) ----
    print("\n[3] 相隔窗口 XOR 熵(接近 8 = 独立, 远低 = 有共同密钥流)")
    for dist in (0x1000, 0x10000, 0x40000):
        if dist + 4096 < len(body):
            x = bytes(a ^ c for a, c in zip(body[:4096], body[dist:dist + 4096]))
            print("   dist=0x%-6X xor-entropy=%.4f" % (dist, ent(x)))


if __name__ == "__main__":
    main()
