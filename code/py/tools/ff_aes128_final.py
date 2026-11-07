#!/usr/bin/env python3
"""最终判定：key 长度由输出缓冲 0x10(16) 决定 → AES-128。
key = RSA 材料前 16 字节，IV 由 cipher_setup 内部从 [ebp-0x14]（输出）取？

实际上：cipher_setup 的 arg2(key)=[ebp-0x14] 是**输出缓冲**（16 字节），
arg3(keylen)=[ebp-0x2c]=RSA 材料。两者被我再次搞反。

从 0xbc86e8: mov ecx,[ebp+0xc] -> 逐字节拷贝 -> 这是 key
而 [ebp+0xc] = arg2 = [ebp-0x14]

所以 [ebp-0x14] 是 key（16 字节输出），[ebp-0x2c] 是 keylen 参数？
但 [ebp-0x2c] 是内存位置，keylen 是数值。

=> 真正的解释：cipher_setup(idx, key_ptr, keylen, iv_ptr, ?, ?, ctx)
   0x483afe lea ecx,[ebp-0x2c]  -> key 数据在 [ebp-0x2c]（RSA 输出）
   0x483b02 lea edx,[ebp-0x14]  -> 另一个 16 字节缓冲
   0x483afc push 0x18           -> keylen=24?

但 0xbc86e8 拷贝的是 [ebp+0xc]。若 arg2=[ebp-0x14]，则 key 来自 [ebp-0x14]。
So [ebp-0x14] 被 cipher_setup 写入 16 字节密钥，再从它读出拷贝。

结论：AES 密钥 = RSA 解出的前 16 字节（AES-128），IV 在 setup 内部由 key 派生或固定。
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
    body = b[koff + ksz:]

    # AES-128: key = mat[:16]
    k16 = mat[:16]
    print("AES-128 key = %s" % k16.hex())
    # 用各种可能的 IV 候选
    ivs = [("zero", b"\0" * 16), ("mat16:32", mat[16:32]),
           ("mat24:40", mat[24:40]), ("ct0", body[:16])]
    for name, iv in ivs:
        for mn in ("ECB", "CBC", "CFB", "OFB", "CTR"):
            try:
                if mn == "ECB":
                    pt = AES.new(k16, AES.MODE_ECB).decrypt(body[:64])
                elif mn == "CBC":
                    pt = AES.new(k16, AES.MODE_CBC, iv).decrypt(body[:64])
                elif mn == "CFB":
                    pt = AES.new(k16, AES.MODE_CFB, iv,
                                 segment_size=128).decrypt(body[:64])
                elif mn == "OFB":
                    pt = AES.new(k16, AES.MODE_OFB, iv).decrypt(body[:64])
                else:
                    pt = AES.new(k16, AES.MODE_CTR, nonce=b"",
                                 initial_value=int.from_bytes(iv, "big")
                                 ).decrypt(body[:64])
            except Exception:
                continue
            pr = sum(1 for c in pt[16:64] if 32 <= c < 127 or c in (9, 10, 13))
            if pt[:9] == b"IWffs100" or pr > 25:
                print("  %-8s %-4s head=%r pr=%d" % (name, mn, pt[:24], pr))


if __name__ == "__main__":
    main()
