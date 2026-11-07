#!/usr/bin/env python3
"""验证分块解密假设：每 8192 字节独立用同一 key/IV 重新开始（代码里每块都 cipher_setup）。
对比：(a) 连续流  (b) 每块重置  —— 看哪种能让后面块也可识别。
"""
import json
import sys


def ent(d):
    from collections import Counter
    import math
    if not d:
        return 0.0
    c = Counter(d)
    n = len(d)
    return -sum((v / n) * math.log(v / n, 2) for v in c.values())


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
                keymat, keyoff = raw[z + 1:], off
                break
    key, iv = keymat[:24], keymat[24:40]
    ct = b[keyoff + ksz:]

    from Crypto.Cipher import AES
    from copy import deepcopy

    for mode in ("CFB", "OFB", "CTR"):
        out = bytearray()
        # (b) 每 8192 重置
        for blk in range(0, len(ct), 8192):
            c = ct[blk:blk + 8192]
            if mode == "CFB":
                o = AES.new(key, AES.MODE_CFB, iv, segment_size=128).decrypt(c)
            elif mode == "OFB":
                o = AES.new(key, AES.MODE_OFB, iv).decrypt(c)
            else:
                o = AES.new(key, AES.MODE_CTR, nonce=b"",
                            initial_value=int.from_bytes(iv, "big")).decrypt(c)
            out += o
        pr = sum(1 for x in out[:256] if 32 <= x < 127 or x in (9, 10, 13))
        pr2 = sum(1 for x in out[8192:8448] if 32 <= x < 127 or x in (9, 10, 13))
        print("[%s 每块重置] blk0 可打印 %.0f%%  blk1 可打印 %.0f%%  头=%r"
              % (mode, 100 * pr / 256, 100 * pr2 / 256, bytes(out[:16])))
        # 块 1 的熵
        print("      blk1 熵=%.2f  head1=%r"
              % (ent(out[8192:8448]), bytes(out[8192:8208])))

    print()
    # (a) 连续流
    for mode in ("CFB", "OFB", "CTR"):
        if mode == "CFB":
            o = AES.new(key, AES.MODE_CFB, iv, segment_size=128).decrypt(ct)
        elif mode == "OFB":
            o = AES.new(key, AES.MODE_OFB, iv).decrypt(ct)
        else:
            o = AES.new(key, AES.MODE_CTR, nonce=b"",
                        initial_value=int.from_bytes(iv, "big")).decrypt(ct)
        pr2 = sum(1 for x in o[8192:8448] if 32 <= x < 127 or x in (9, 10, 13))
        print("[%s 连续] blk1 可打印 %.0f%%  head=%r" % (mode, 100 * pr2 / 256,
                                                         o[8192:8208]))


if __name__ == "__main__":
    main()
