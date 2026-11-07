#!/usr/bin/env python3
"""关键检验：CFB128 下，前 16 字节正确意味着 E(IV) 正确。
若第二块（16..32）解错，则 IV2 != 前 16 字节密文。

但如果明文第 16..32 字节本身是**不可识别的随机数据**（例如压缩数据），
则"解错"的判定不成立。需要找可判据：明文 16.. 是否低熵/有结构。

用大样本：如果 key/IV/模式都对，那么整块的熵应该不等于 8。
"""
import json
import math
import sys
from collections import Counter

from Crypto.Cipher import AES


def ent(d):
    if not d:
        return 0
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
                mat, koff = raw[z + 1:], off
                break
    key, iv = mat[:24], mat[24:40]
    body = b[koff + ksz:]
    print("密文熵: %.4f" % ent(body[:8192]))
    pt = AES.new(key, AES.MODE_CFB, iv, segment_size=128).decrypt(body)
    print("CFB128 解密后熵: %.4f" % ent(pt[:8192]))
    print("前 32: %r" % pt[:32])
    # 如果对，4096 字节应该有结构
    print("后 8192 熵: %.4f" % ent(pt[8192:16384]))
    # 对比：直接用密文（未解密）的熵
    print("\n逐块解密后熵（前 6 块）:")
    for i in range(6):
        seg = pt[i * 8192:(i + 1) * 8192]
        if len(seg) < 100:
            break
        pr = sum(1 for c in seg if 32 <= c < 127 or c in (9, 10, 13))
        print("  blk%d 熵=%.3f  可打印=%.1f%%" % (i, ent(seg), 100 * pr / len(seg)))


if __name__ == "__main__":
    main()
