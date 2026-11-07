#!/usr/bin/env python3
"""用密文反馈（CFB 链）验证：块1 的 IV = 块0 最后 16 字节密文。
若正确，块 1 开头应能解出 IWffs100 或可识别结构。
另外尝试：块 1 的 IV = 块 0 最后 16 字节【明文】(CBC 风格)。
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
    print("body len = %d, 8192*%d + %d"
          % (len(body), len(body) // 8192, len(body) % 8192))

    # 块0 解密
    blk0_c = body[:8192]
    blk0_p = AES.new(key, AES.MODE_CFB, iv, segment_size=128).decrypt(blk0_c)
    print("blk0 头: %r" % blk0_p[:24])
    print("blk0 尾16(明文): %s" % blk0_p[-16:].hex(" "))
    print("blk0 尾16(密文): %s" % blk0_c[-16:].hex(" "))

    # 块1 的几种 IV 候选
    cands = {
        "ct_prev": blk0_c[-16:],
        "pt_prev": blk0_p[-16:],
        "iv": iv,
        "blk1_ct_head": body[8192:8208],
    }
    print("\n块1 (body[8192:8192+32]) 密文: %s" % body[8192:8224].hex(" "))
    for name, civ in cands.items():
        for mn in ("CFB", "OFB"):
            try:
                if mn == "CFB":
                    o = AES.new(key, AES.MODE_CFB, civ,
                                segment_size=128).decrypt(body[8192:8260])
                else:
                    o = AES.new(key, AES.MODE_OFB, civ).decrypt(body[8192:8260])
            except Exception:
                continue
            pr = sum(1 for c in o if 32 <= c < 127 or c in (9, 10, 13))
            mark = "★" if b"IWff" in o or pr > 40 else ""
            print("  iv=%-12s %s -> %r  (pr=%d)%s" % (name, mn, o[:32], pr, mark))


if __name__ == "__main__":
    main()
