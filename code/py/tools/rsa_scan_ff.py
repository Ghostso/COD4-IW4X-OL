#!/usr/bin/env python3
"""系统扫描 .ff：在前 N 字节内滑动 256 字节窗口，做 RSA 解密，
找 PKCS#1 v1.5 填充 (00 02 <非零...> 00 <明文>) 的命中位置。

用户已明确授权使用提取的私钥做此验证。
"""
import json
import sys


def load_key(path):
    d = json.load(open(path, encoding="utf-8"))
    return int(d["n"]), int(d["d"])


def try_block(blk, n, d, k):
    if len(blk) != k:
        return None
    c = int.from_bytes(blk, "big")
    if c >= n:
        return None
    m = pow(c, d, n)
    return m.to_bytes(k, "big")


def main():
    keyf = r"_byte_papers\rsa_private_key.json"
    path = sys.argv[1]
    scan = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x1000
    n, d = load_key(keyf)
    k = (n.bit_length() + 7) // 8
    b = open(path, "rb").read()
    print("file=%s size=%d  密钥块长=%d  扫描前 %#x 字节" % (
        path.rsplit("\\", 1)[-1], len(b), k, scan))

    found = 0
    for off in range(0, min(scan, len(b) - k + 1)):
        blk = b[off:off + k]
        m = try_block(blk, n, d, k)
        if m is None:
            continue
        if m[0] == 0 and m[1] == 2:
            # PKCS#1 v1.5 加密填充：00 02 <>=8 非零随机> 00 <数据>
            z = m.find(b"\x00", 2)
            if z > 10:
                data = m[z + 1:]
                print("  ★ 命中 offset=%#x  pad=PKCS#1v1.5  明文 %d 字节: %s"
                      % (off, len(data), data[:64].hex(" ")))
                if len(data) <= 64 and all(32 <= c < 127 for c in data):
                    print("       ASCII: %r" % data.decode())
                found += 1
        elif m[0] == 0 and m[1] == 1:
            print("  签名填充 offset=%#x" % off)
            found += 1
    if not found:
        print("  未找到 PKCS#1 命中")


if __name__ == "__main__":
    main()
