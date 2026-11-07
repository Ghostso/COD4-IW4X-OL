#!/usr/bin/env python3
"""穷举 24 字节切位：材料 40 字节 -> 找 24 字节窗口，覆盖所有起点。
并用三种判定同时要求：(a) 头 IWffs100 (b) 16..32 非随机 (c) 能被 zlib 或含 ASCII 关键词。
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
                mat, koff = raw[z + 1:], off
                break
    body = b[koff + ksz:]
    tail = b[-64:]
    print("mat =%s" % mat.hex())
    print("tail=%s" % tail.hex())
    print("body len=%d" % len(body))

    pools = {"mat": mat, "tail": tail, "mat+tail": mat + tail}
    results = []
    for pn, pool in pools.items():
        for ks in range(0, len(pool) - 23):
            key = pool[ks:ks + 24]
            for ivs in range(0, len(pool) - 15):
                iv = pool[ivs:ivs + 16]
                for mn in ("CFB", "OFB"):
                    try:
                        if mn == "CFB":
                            pt = AES.new(key, AES.MODE_CFB, iv,
                                         segment_size=128).decrypt(body[:2048])
                        else:
                            pt = AES.new(key, AES.MODE_OFB, iv
                                         ).decrypt(body[:2048])
                    except Exception:
                        continue
                    if pt[:9] != b"IWffs100":
                        continue
                    seg = pt[16:528]
                    pr = sum(1 for c in seg
                             if 32 <= c < 127 or c in (9, 10, 13))
                    results.append((pr, pn, ks, ivs, mn, pt[:40]))
    results.sort(reverse=True)
    print("\n头匹配结果 %d 个：" % len(results))
    for pr, pn, ks, ivs, mn, head in results[:10]:
        print("  printable(16..528)=%d/%d  %s key@%d iv@%d %s"
              % (pr, 512, pn, ks, ivs, mn))
        print("     %r" % head)


if __name__ == "__main__":
    main()
