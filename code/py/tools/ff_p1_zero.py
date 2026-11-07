#!/usr/bin/env python3
"""检查 16..32 全零是否是"块1的 IV"，然后 32.. 是否属于新流。"""
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
    key = mat[:24]
    body = b[koff + ksz:]
    ecb = AES.new(key, AES.MODE_ECB)

    # 解开前 32 字节
    p0 = b"IWffs100" + b"\x00" * 8
    eiv0 = bytes(a ^ c for a, c in zip(p0, body[:16]))
    iv0 = ecb.decrypt(eiv0)
    # 用 iv0 解 16..32（CFB 标准：IV2 = C0）
    # 期望 P1 = zeros；验算
    e1 = ecb.encrypt(body[:16])
    p1 = bytes(a ^ c for a, c in zip(e1, body[16:32]))
    print("P1 =", p1.hex(), "  (期望全零)")
    print("P1 all zero?", p1 == b"\x00" * 16)

    # 若 P1 是 zeros，那么第 32 字节起是什么？
    # 假设：16..32 是"下一个 IV"，即用 body[:32] 解 not working.
    # 假设：真正的密文从 32 开始，IV = P1（zeros）
    zero_iv = b"\x00" * 16
    for name, iv in (("zeros", zero_iv), ("iv0", iv0)):
        for mn in ("CFB", "OFB"):
            try:
                if mn == "CFB":
                    pt = AES.new(key, AES.MODE_CFB, iv,
                                 segment_size=128).decrypt(body[32:32 + 512])
                else:
                    pt = AES.new(key, AES.MODE_OFB, iv).decrypt(body[32:32 + 512])
            except Exception:
                continue
            pr = sum(1 for c in pt if 32 <= c < 127 or c in (9, 10, 13))
            print("[%s %s] printable=%d/512 head=%r"
                  % (name, mn, pr, pt[:32]))


if __name__ == "__main__":
    main()
