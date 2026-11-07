#!/usr/bin/env python3
"""在已确定的 key/IV 下，判定流模式并解出完整明文。

通过检查明文的结构特征（可打印率、已知关键字、尾部 hash）来判断。
"""
import hashlib
import json
import sys
import zlib

from Crypto.Cipher import AES


def main():
    ff = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else None
    kd = json.load(open(r"_byte_papers\rsa_private_key.json", encoding="utf-8"))
    n, dp = int(kd["n"]), int(kd["d"])
    ksz = (n.bit_length() + 7) // 8
    b = open(ff, "rb").read()
    keymat = None
    for off in range(0, min(0x2000, len(b) - ksz)):
        m = pow(int.from_bytes(b[off:off + ksz], "big"), dp, n)
        raw = m.to_bytes(ksz, "big")
        if raw[0] == 0 and raw[1] == 2:
            z = raw.find(b"\x00", 2)
            if z > 10:
                keymat, keyoff = raw[z + 1:], off
                break
    key, iv = keymat[:24], keymat[24:40]
    ds = keyoff + ksz
    ct = b[ds:]
    print("key=%s\niv =%s\ndata @%#x len=%d" % (key.hex(), iv.hex(), ds, len(ct)))

    best = None
    for mn in ("CFB", "OFB", "CTR"):
        if mn == "CFB":
            pt = AES.new(key, AES.MODE_CFB, iv, segment_size=128).decrypt(ct)
        elif mn == "OFB":
            pt = AES.new(key, AES.MODE_OFB, iv).decrypt(ct)
        else:
            pt = AES.new(key, AES.MODE_CTR, nonce=b"",
                         initial_value=int.from_bytes(iv, "big")).decrypt(ct)
        pr = sum(1 for c in pt[:512] if 32 <= c < 127 or c in (9, 10, 13))
        print("\n[%s] head=%r 可打印率(前512)=%.1f%%" % (mn, pt[:20], 100 * pr / 512))
        if best is None or pr > best[0]:
            best = (pr, mn, pt)

    _, mn, pt = best
    print("\n★ 判定模式 = %s" % mn)
    print("头 64: %r" % pt[:64])
    print("hex   : %s" % pt[:64].hex(" "))

    # 尝试 zlib
    for off in range(0, 32):
        for wb in (15, -15, 31):
            try:
                d = zlib.decompressobj(wb).decompress(pt[off:])
                if len(d) > 1000:
                    print("\n★★ zlib off=%d wbits=%d -> %d 字节" % (off, wb, len(d)))
                    print("  前 300: %r" % d[:300])
                    if out:
                        open(out + ".z", "wb").write(d)
                    break
            except Exception:
                pass

    # 尾部 hash 校验
    if len(pt) > 64:
        body, h = pt[:-64], pt[-64:]
        print("\nbody len=%d" % len(body))
        print("sha256(body) = %s" % hashlib.sha256(body).hexdigest())
        print("tail[:32]    = %s" % h[:32].hex())
        print("tail[32:]    = %s" % h[32:].hex())
        print("匹配前32: %s   匹配后32: %s" % (
            hashlib.sha256(body).hexdigest() == h[:32].hex(),
            hashlib.sha256(body).hexdigest() == h[32:].hex()))
    if out:
        open(out, "wb").write(pt)
        print("\n已写出 %s" % out)


if __name__ == "__main__":
    main()
