#!/usr/bin/env python3
"""用已确认的 key/IV，测试 libtomcrypt 的各 CFB 变体：
CFB8 / CFB64 / CFB128，以及 CTR 的不同计数器起始。
libtomcrypt 的 cfb_start 有 cfb8 / cfb64 / cfb128 三种。
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
    print("key=" + key.hex())
    print("iv =" + iv.hex())
    print("body len", len(body))

    for seg in (8, 64, 128):
        try:
            pt = AES.new(key, AES.MODE_CFB, iv,
                         segment_size=seg).decrypt(body[:1024])
        except Exception as e:
            print("seg", seg, "err", e)
            continue
        pr = sum(1 for c in pt[16:528] if 32 <= c < 127 or c in (9, 10, 13))
        print("\nCFB%d  头=%r" % (seg, pt[:24]))
        print("   16..80: %r" % pt[16:80])
        print("   printable(16..528)=%d/512" % pr)

    # 也试 ECB 逐块
    pt = AES.new(key, AES.MODE_ECB).decrypt(body[:1024])
    pr = sum(1 for c in pt[16:528] if 32 <= c < 127 or c in (9, 10, 13))
    print("\nECB 头=%r  printable=%d/512" % (pt[:24], pr))
    print("   16..80: %r" % pt[16:80])


if __name__ == "__main__":
    main()
