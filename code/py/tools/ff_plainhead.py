#!/usr/bin/env python3
"""验证：.ff 明文头结构。前 16 字节由 IV 决定（密钥流首块），
16..48 在所有 IV 下相同 => 那 32 字节是明文，或是"重置后的稳定流"。

直接看密文头区域的结构：IWff0100 (磁盘) / IWffs100 (明文)。
打印磁盘头 + 解密头对照，找字段。
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
    print("== 磁盘文件头 ==")
    print("  0x00: %r" % b[:16])
    print("  0x08 u32=%d  0x0c u32=%d  0x10 u32=%d"
          % (struct.unpack_from("<I", b, 8)[0],
             struct.unpack_from("<I", b, 12)[0],
             struct.unpack_from("<I", b, 16)[0]))
    print("  0x14: %s" % b[0x14:0x20].hex(" "))

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
    pt = AES.new(key, AES.MODE_CFB, iv, segment_size=128).decrypt(body[:256])

    print("\n== 明文头（CFB128 解出前 256）==")
    for i in range(0, 96, 16):
        print("  +%02d: %s  |%s|" % (
            i, pt[i:i + 16].hex(" "),
            "".join(chr(c) if 32 <= c < 127 else "." for c in pt[i:i + 16])))

    # 尝试把 16..80 当明文结构解析
    print("\n== 若 16.. 是明文 u32 序列 ==")
    for i in range(16, 64, 4):
        print("  +%02d u32=%#010x (%d)" % (i,
              struct.unpack_from("<I", pt, i)[0],
              struct.unpack_from("<I", pt, i)[0]))


if __name__ == "__main__":
    main()
