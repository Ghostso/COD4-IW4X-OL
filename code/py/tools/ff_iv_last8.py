#!/usr/bin/env python3
"""E(IV) 前 8 字节 = fb7a889474d088a0。
已知 IV 前 8 = mat[24:32]，后 8 未知。

但 AES 是完全雪崩的：改任意一个字节，输出全部变。
所以"前 8 字节匹配"意味着 **IV 的前 8 字节正确，且后 8 字节也正确**…
除非 libtomcrypt 的 CFB 实现只用了前 8 字节。

结论：如果 E(IV)[0:8] 对，而 E(IV)[8:16] 不对，
唯一的解释是 **libtomcrypt 的 CFB 在内部对 IV 做了某种变换**（例如
cfb_start 把 IV 按大端 u32 装，但我们用标准 CFB 加密整 16 字节）。

正确做法：用 libtomcrypt 的语义复现 —— 它的 cfb128 在开始时
st->iv 就是 4 个大端 u32。加密时用它当计数器。

但标准 CFB128 与它就是一致的。除非……

等等：E(IV)[0:8] 对上，说明 IV 的**前 8 字节**在 AES 输入的前 8 位
上正确。AES 的雪崩只影响输出，不影响"输入前 8 字节对应输出前 8 字节"。
所以 IV 前 8 对是正常的。

后 8 不对 ⇒ IV 后 8 字节不是 mat[32:40]。
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

    # 只验证：IV 前 8 是 mat[24:32] 吗？
    # 用前 8 匹配 + 后 8 全零
    iv = mat[24:32] + b"\0" * 8
    print("iv  =", iv.hex())
    print("E(iv)=", ecb.encrypt(iv).hex())
    print("need =", eiv.hex())
    print("前8对:", ecb.encrypt(iv)[:8] == eiv[:8])
    print()
    # 穷举后 8 字节：从 mat 的其他位置、tail、文件里找
    tail = b[-64:]
    cands = []
    for src_name, src in (("mat", mat), ("tail", tail),
                          ("body", body[:64])):
        for i in range(0, max(1, len(src) - 7)):
            cands.append(("%s[%d:%d]" % (src_name, i, i + 8), src[i:i + 8]))
    hit = 0
    for name, last8 in cands:
        iv = mat[24:32] + last8
        if ecb.encrypt(iv) == eiv:
            print("★★★ 命中 IV =", iv.hex(), " 后8来自", name)
            hit += 1
    print("命中", hit)


if __name__ == "__main__":
    main()
