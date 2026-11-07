#!/usr/bin/env python3
"""libtomcrypt 的 cfb_start 把 IV 读成 4 个大端 u32。
若它读的是一个"内部数组"，而我们送的 IV 是网络序字节，
则它在内部按大端解释 —— 但这不影响最终加密的字节序列。
真正影响的是：它取的是 iv[0..3] 作为第一个 word。

关键：E(IV) 前 8 字节对、后 8 字节错。
前 8 = iv[0:8] 参与的结果对。后 8 错=> 后 8 字节的 IV 输入不同。

假设：libtomcrypt 的 cfb 只用前 8 字节 IV（或它把 IV 当 2 个 u64）。
测试：把 IV 的后 8 字节替换成别的值，看 E(IV) 后 8 是否变化。
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
    key = mat[:24]
    body = b[koff + ksz:]
    p0 = b"IWffs100" + b"\x00" * 8
    eiv = bytes(a ^ c for a, c in zip(p0, body[:16]))
    ecb = AES.new(key, AES.MODE_ECB)

    print("E(IV) needed =", eiv.hex())
    print("E(mat[24:40])=", ecb.encrypt(mat[24:40]).hex())
    print()
    print("若只前 8 字节匹配，测试 IV 的后 8 字节取不同来源：")
    cands = {
        "mat[24:32]+zeros": mat[24:32] + b"\0" * 8,
        "zeros+mat[32:40]": b"\0" * 8 + mat[32:40],
        "mat[32:40]*2": mat[32:40] * 2,
        "mat[24:32]*2": mat[24:32] * 2,
        "ct[:8]+mat[32:40]": body[:8] + mat[32:40],
        "mat[24:32]+ct[:8]": mat[24:32] + body[:8],
    }
    for name, iv in cands.items():
        e = ecb.encrypt(iv)
        ok = e[:8] == eiv[:8]
        ok2 = e == eiv
        print("  %-22s E(iv)=%s 前8对=%s 全对=%s"
              % (name, e.hex(), ok, ok2))


if __name__ == "__main__":
    main()
