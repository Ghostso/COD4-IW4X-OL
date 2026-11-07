#!/usr/bin/env python3
"""descriptor: block_length=6, iv_len=16, flags=0xa。
libtomcrypt 的 CFB 支持任意块粒度。试试 6 字节粒度的 CFB 变体。
"""
import json
import sys

from Crypto.Cipher import AES


def cfb_var(key, iv, data, n):
    """通用 CFB-n（n 字节粒度）"""
    out = bytearray()
    reg = bytearray(iv)
    i = 0
    aes = AES.new(key, AES.MODE_ECB)
    while i < len(data):
        ks = aes.encrypt(bytes(reg))
        chunk = min(n, len(data) - i)
        blk = bytearray(data[i:i + chunk])
        for j in range(chunk):
            out.append(blk[j] ^ ks[j])
        # 反馈：把密文块移入寄存器
        reg = bytearray(reg[chunk:]) + bytearray(bytes(blk)[:chunk])
        i += chunk
    return bytes(out)


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
    for N in (1, 2, 4, 6, 8, 16):
        pt = cfb_var(key, iv, body[:512], N)
        pr = sum(1 for c in pt[:48] if 32 <= c < 127 or c in (9, 10, 13))
        print("CFB%d: head=%r pr=%d/48" % (N, pt[:40], pr))


if __name__ == "__main__":
    main()
