#!/usr/bin/env python3
"""目标：解出块 0 的完整明文。已知前 16 字节是 IWffs100+全零。
若块 0 明文是 zlib 压缩流，则前 16 字节应是 zlib 头 — 但不是。
所以块 0 有独立格式。检查：明文 16 字节后是什么结构。
"""
import json
import sys
import zlib

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
                keymat, keyoff = raw[z + 1:], off
                break
    key, iv = keymat[:24], keymat[24:40]
    data0 = keyoff + ksz
    blk0 = b[data0:data0 + 8192]

    for mn in ("CFB", "OFB", "CTR"):
        if mn == "CFB":
            pt = AES.new(key, AES.MODE_CFB, iv, segment_size=128).decrypt(blk0)
        elif mn == "OFB":
            pt = AES.new(key, AES.MODE_OFB, iv).decrypt(blk0)
        else:
            pt = AES.new(key, AES.MODE_CTR, nonce=b"",
                         initial_value=int.from_bytes(iv, "big")).decrypt(blk0)
        print("\n=== %s ===" % mn)
        print("前 16 : %s" % pt[:16].hex(" "))
        print("16..48: %s" % pt[16:48].hex(" "))
        print("repr  : %r" % pt[:48])
        # 在块内找 zlib
        for i in range(0, 128):
            if pt[i] == 0x78 and pt[i + 1] in (0x01, 0x9C, 0xDA):
                try:
                    d = zlib.decompressobj().decompress(pt[i:])
                    if len(d) > 100:
                        print("  ★ zlib @%d -> %d" % (i, len(d)))
                        print("  %r" % d[:200])
                except Exception:
                    pass
        # 尾部
        print("尾 16 : %s" % pt[-16:].hex(" "))


if __name__ == "__main__":
    main()
