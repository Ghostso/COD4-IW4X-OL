#!/usr/bin/env python3
"""检验：CFB128 下，若只有第一块对，说明后续块用不同 IV。
从密文和解出的明文前 16 字节，反推每一块的实际 IV 序列，看是否有规律。
"""
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
    key, iv = mat[:24], mat[24:40]
    body = b[koff + ksz:]

    ecb = AES.new(key, AES.MODE_ECB)

    # CFB128 解密前 4 块，逐块看
    ct = body[:64]
    pt = AES.new(key, AES.MODE_CFB, iv, segment_size=128).decrypt(ct)
    for i in range(4):
        print("块%d: ct=%s  pt=%r" % (i, ct[i * 16:i * 16 + 16].hex(" "),
                                     pt[i * 16:i * 16 + 16]))

    # 若第 2 块的 IV 是"前块密文"，我们已经那样做了（CFB 标准），
    # 所以第 2 块解错说明密文不是连续流。
    # 检验：如果用 ECB 解每一块，能否得到规律？
    print("\nECB 逐块:")
    for i in range(4):
        d = ecb.decrypt(ct[i * 16:i * 16 + 16])
        print("  块%d -> %s" % (i, d.hex(" ")))

    # 检验：xor 前 16 字节明文与密文，得到 E(IV)
    p0 = b"IWffs100" + b"\x00" * 8
    x = bytes(a ^ c for a, c in zip(p0, ct[:16]))
    eiv = x   # = E(IV)
    print("\nP0^C0 = %s  (应等于 E(IV))" % x.hex(" "))
    # 用 ECB 加密我们的 iv，看是否等于它
    print("E(iv)  = %s" % ecb.encrypt(iv).hex(" "))
    print("相等? %s" % (ecb.encrypt(iv) == eiv))

    # 第 2 块，标准 CFB：IV2 = C0
    print("\n第2块 IV 候选 E(x) 比较：")
    for name, cand in (("C0", ct[:16]), ("iv", iv),
                       ("P0", p0), ("D(C0)", ecb.decrypt(ct[:16]))):
        e = ecb.encrypt(cand)
        need = bytes(a ^ c for a, c in zip(e, ct[16:32]))
        print("  iv=%-6s E(iv)=%s -> P1 会是 %r"
              % (name, e.hex()[:32], need))
