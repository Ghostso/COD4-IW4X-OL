#!/usr/bin/env python3
"""验证 IV/密钥的字节序解释：
libtomcrypt 的 cfb_start 把 IV 当 4 个 u32 大端装入。
若我们送的 IV 字节顺序与它不一致，前 16 字节仍可能碰巧正确（因为只用一次），
但后续会错。测试 IV 的 4 种重排。
"""
import json
import struct
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
    key, iv0 = mat[:24], mat[24:40]
    body = b[koff + ksz:]

    def rev32(x):
        return b"".join(x[i:i + 4][::-1] for i in range(0, 16, 4))

    ivs = {
        "raw": iv0,
        "rev32": rev32(iv0),
        "rev16": iv0[::-1],
        "u32le_as_be": b"".join(struct.pack(">I", struct.unpack_from(
            "<I", iv0, i)[0]) for i in range(0, 16, 4)),
        "u32be_as_le": b"".join(struct.pack("<I", struct.unpack_from(
            ">I", iv0, i)[0]) for i in range(0, 16, 4)),
    }
    for name, iv in ivs.items():
        for seg in (128,):
            pt = AES.new(key, AES.MODE_CFB, iv,
                         segment_size=seg).decrypt(body[:1024])
            pr = sum(1 for c in pt[16:528] if 32 <= c < 127 or c in (9, 10, 13))
            print("%-12s iv=%s" % (name, iv.hex()))
            print("   head=%r  printable=%d/512" % (pt[:32], pr))
            if pr > 400:
                print("   ★★ 可能是正确的 IV")


if __name__ == "__main__":
    main()
