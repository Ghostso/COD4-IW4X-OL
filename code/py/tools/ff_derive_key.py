#!/usr/bin/env python3
"""给定 RSA 解出的 40 字节密钥材料，尝试推导 AES 密钥并解密 .ff 数据块。"""
import json
import struct
import sys

import zlib


def load_key(p=" _byte_papers\\rsa_private_key.json".strip()):
    d = json.load(open(p, encoding="utf-8"))
    return int(d["n"]), int(d["d"])


def rsa_block(b, off, n, d, k):
    m = pow(int.from_bytes(b[off:off + k], "big"), d, n)
    raw = m.to_bytes(k, "big")
    if raw[0] != 0 or raw[1] != 2:
        return None
    z = raw.find(b"\x00", 2)
    return raw[z + 1:] if z > 10 else None


def main():
    path = sys.argv[1]
    n, d = load_key()
    k = (n.bit_length() + 7) // 8
    b = open(path, "rb").read()

    # 找 RSA 块
    keymat = None
    keyoff = None
    for off in range(0, min(0x2000, len(b) - k)):
        km = rsa_block(b, off, n, d, k)
        if km:
            keymat, keyoff = km, off
            break
    if not keymat:
        print("未找到 RSA 块")
        return
    print("RSA 块 @%#x，解出 %d 字节: %s" % (keyoff, len(keymat), keymat.hex(" ")))

    # .ff 头
    print("\nIWff 头: %s" % b[:24].hex(" "))
    v8 = struct.unpack_from("<I", b, 8)[0]
    v12 = struct.unpack_from("<I", b, 12)[0]
    print("  u32@8=%d  u32@12=%d" % (v8, v12))

    # 数据起点 = RSA 块之后
    data_start = keyoff + k
    print("数据起点 = %#x" % data_start)

    if len(sys.argv) > 2:
        for keyarg in sys.argv[2:]:
            if keyarg.startswith("hex:"):
                key = bytes.fromhex(keyarg[4:])
            else:
                key = keymat[:int(keyarg)]
            print("\n尝试密钥 len=%d: %s" % (len(key), key.hex()))
            try:
                from Crypto.Cipher import AES
                dec = AES.new(key, AES.MODE_ECB).decrypt(
                    b[data_start:data_start + 64])
                print("  ECB 解出: %s" % dec[:32].hex(" "))
            except ImportError:
                print("  缺 pycryptodome")


if __name__ == "__main__":
    main()
