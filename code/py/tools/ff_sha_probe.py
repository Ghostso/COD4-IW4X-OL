#!/usr/bin/env python3
"""代码里 0x483787 分支：解出 8192 字节后
  sha256(plaintext) 与 ctx 中的 32 字节摘要比较 (0x483802-0x483822)。

若我们能找到 ctx 里的那个摘要，就能用"sha256 匹配"作为唯一判据，
从而穷举出正确的 key/IV/mode/dataoffset。

摘要可能就藏在文件里（如尾部 64 字节）。
先验证：tail[:32] 或 tail[32:] 是否等于 sha256(某种解密的 8192 字节)。
"""
import hashlib
import json
import sys

from Crypto.Cipher import AES


def main():
    ff = sys.argv[1]
    kd = json.load(open(r"_byte_papers\rsa_private_key.json", encoding="utf-8"))
    n, dp = int(kd["n"]), int(kd["d"])
    ksz = (n.bit_length() + 7) // 8
    b = open(ff, "rb").read()
    for off in range(0, min(0x2000, len(b) - ksz)):
        m = pow(int.from_bytes(b[off:off + ksz], "big"), dp, n)
        raw = m.to_bytes(ksz, "big")
        if raw[0] == 0 and raw[1] == 2:
            z = raw.find(b"\x00", 2)
            if z > 10:
                mat, koff = raw[z + 1:], off
                break
    body = b[koff + ksz:]
    tails = {"tail[:32]": b[-64:-32], "tail[32:]": b[-32:]}

    keys = {"mat[:24]": mat[:24], "mat[16:40]": mat[16:40],
            "mat[:16]": mat[:16], "mat[24:40]": mat[24:40]}
    ivs = {"mat[24:40]": mat[24:40], "zero": b"\0" * 16,
           "mat[16:32]": mat[16:32], "mat[:16]": mat[:16]}
    starts = [0, 4, 16, 0x100, 0x115 - (koff + ksz), 0x40]

    found = 0
    for ds in set(x for x in starts if x >= 0):
        for kn, key in keys.items():
            for ivn, iv in ivs.items():
                for mn in ("CFB", "OFB", "CTR", "CBC"):
                    try:
                        if mn == "CFB":
                            pt = AES.new(key, AES.MODE_CFB, iv,
                                         segment_size=128).decrypt(
                                             body[ds:ds + 8192])
                        elif mn == "OFB":
                            pt = AES.new(key, AES.MODE_OFB, iv).decrypt(
                                body[ds:ds + 8192])
                        elif mn == "CTR":
                            pt = AES.new(key, AES.MODE_CTR, nonce=b"",
                                         initial_value=int.from_bytes(iv, "big")
                                         ).decrypt(body[ds:ds + 8192])
                        else:
                            pt = AES.new(key, AES.MODE_CBC, iv).decrypt(
                                body[ds:ds + 8192])
                    except Exception:
                        continue
                    h = hashlib.sha256(pt).digest()
                    for tn, tv in tails.items():
                        if h == tv:
                            print("★★★ SHA256 匹配! ds=%#x %s %s %s -> %s"
                                  % (ds, kn, ivn, mn, tn))
                            found += 1
    print("匹配数：%d" % found)
    if not found:
        print("\n（没有 SHA256 匹配；说明 tail 不是该块的摘要，"
              "或 key/iv/模式/起点仍不对）")


if __name__ == "__main__":
    main()
