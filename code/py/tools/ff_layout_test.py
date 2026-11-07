#!/usr/bin/env python3
"""决定性检验：40 字节材料中，**后 24 字节**作为 key（前 16 作 IV）的假设。
libtomcrypt 的 rsa_decrypt_key_ex 输出格式是 [密钥][hash]，共 40 字节：
  - 若 key 24 + hash 16 → key 在前
  - 若 hash 16 + key 24 → key 在后
逐一验证，判据：解出的正文熵 < 7.5 或含 zlib/可见结构。
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
    body = b[koff + ksz:]
    print("mat: %s" % mat.hex())
    print("body 熵 %.3f" % ent(body[:4096]))

    layouts = {
        "key=mat[0:24] iv=mat[24:40]": (mat[0:24], mat[24:40]),
        "key=mat[16:40] iv=mat[0:16]": (mat[16:40], mat[0:16]),
        "key=mat[0:16] iv=mat[16:32]": (mat[0:16], mat[16:32]),
        "key=mat[24:40]+0 iv=0":       (mat[24:40] + b"\0" * 8, b"\0" * 16),
    }
    for name, (key, iv) in layouts.items():
        for mn in ("CFB", "OFB", "CTR"):
            try:
                if mn == "CFB":
                    pt = AES.new(key, AES.MODE_CFB, iv,
                                 segment_size=128).decrypt(body[:4096])
                elif mn == "OFB":
                    pt = AES.new(key, AES.MODE_OFB, iv).decrypt(body[:4096])
                else:
                    pt = AES.new(key, AES.MODE_CTR, nonce=b"",
                                 initial_value=int.from_bytes(iv, "big")
                                 ).decrypt(body[:4096])
            except Exception:
                continue
            e = ent(pt[:4096])
            pr = sum(1 for c in pt[:256] if 32 <= c < 127 or c in (9, 10, 13))
            mark = " ★★★" if e < 7.0 else (" ★" if pr > 100 else "")
            print("%-30s %s 熵=%.3f pr=%d%s" % (name, mn, e, pr, mark))
            if e < 7.0:
                print("     头: %r" % pt[:64])


if __name__ == "__main__":
    main()
