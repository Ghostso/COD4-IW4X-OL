#!/usr/bin/env python3
"""用内嵌 RSA 私钥尝试解密 .ff 的相关段落。

不做假设，逐个位置试：
  - IWff0100 之后的 16 字节是否是 RSA 密文（512 字节？）
  - 载荷开头 256/512 字节是否是 RSA 密文
"""
import json
import os
import sys


def load_key(path):
    d = json.load(open(path, encoding="utf-8"))
    return {k: (int(v) if k != "ver" else v) for k, v in d.items()}


def rsa_dec(c, n, d):
    k = (n.bit_length() + 7) // 8
    if len(c) != k:
        return None
    m = pow(int.from_bytes(c, "big"), d, n)
    return m.to_bytes(k, "big")


def main():
    keyf = sys.argv[1]
    f = sys.argv[2]
    off = int(sys.argv[3], 0) if len(sys.argv) > 3 else None
    k = load_key(keyf)
    n, d = k["n"], k["d"]
    keylen = (n.bit_length() + 7) // 8
    print("RSA: n=%d bits, 密文块长=%d" % (n.bit_length(), keylen))

    b = open(f, "rb").read()
    i = b.find(b"IWff")
    print("IWff 在 %#x" % i)
    body = b[(i + 24) if i >= 0 else 0:]
    candidates = []
    if off is not None:
        candidates = [(off, b[off:off + keylen])]
    else:
        for o in (0, 24, 4, 8, 16):
            if len(body) >= o + keylen:
                candidates.append((o, body[o:o + keylen]))

    for o, c in candidates:
        m = rsa_dec(c, n, d)
        if m is None:
            print("  偏移 %#x: 长度不足" % o)
            continue
        # PKCS#1 v1.5: 00 02 <random> 00 <data>
        pad = m[:2].hex()
        print("  偏移 %#x 解出前 32: %s  (pad=%s)" % (
            o, m[:32].hex(" "), pad))
        if m[0] == 0 and m[1] == 2:
            z = m.find(b"\x00", 2)
            print("      ★ PKCS#1 v1.5 结构!  数据 = %s" % m[z + 1:z + 49].hex())
        elif m[0] == 0 and m[1] == 1:
            print("      PKCS#1 v1.5 签名填充")
        else:
            print("      非标准填充")


if __name__ == "__main__":
    main()
