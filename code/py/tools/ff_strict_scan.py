#!/usr/bin/env python3
"""严格扫描：用 RSA 解出的 40 字节各种切法做 AES 密钥，
对多个数据起点、多种模式，**只认** 明文头 == b'IWffs100' 或可 zlib 解压。
"""
import json
import sys
import zlib

from Crypto.Cipher import AES

GOOD = b"IWffs100"


def main():
    ff = sys.argv[1]
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
    print("keymat @%#x (%d): %s" % (keyoff, len(keymat), keymat.hex()))
    print("file size %d" % len(b))

    # 候选密钥：材料本身各切法 + 两侧填充
    keys = {}
    for a in range(0, len(keymat) - 15):
        for L in (16, 24, 32):
            if a + L <= len(keymat):
                keys["mat[%d:%d]" % (a, a + L)] = keymat[a:a + L]
    # 也试材料 + 尾部 64 / 头部
    tail = b[-64:]
    for a in range(0, 49):
        for L in (16, 24, 32):
            if a + L <= 64:
                keys["tail[%d:%d]" % (a, a + L)] = tail[a:a + L]

    starts = set()
    for d in range(0, 0x20):
        starts.add(keyoff + ksz + d)
    for d in (0, 4, 8, 16, 24, 32, 48, 64, 0x40):
        starts.add(d)
    ivs = [("zero", b"\0" * 16)] + [
        ("mat[%d:%d]" % (i, i + 16), keymat[i:i + 16])
        for i in range(0, len(keymat) - 15)]

    hits = 0
    for kn, key in keys.items():
        for ds in sorted(starts):
            if ds + 32 > len(b):
                continue
            ct = b[ds:ds + 64]
            for ivn, iv in ivs:
                for mn in ("ECB", "CBC", "CFB", "OFB", "CTR"):
                    try:
                        if mn == "ECB":
                            dec = AES.new(key, AES.MODE_ECB).decrypt(ct[:32])
                        elif mn == "CBC":
                            dec = AES.new(key, AES.MODE_CBC, iv).decrypt(ct[:32])
                        elif mn == "CFB":
                            dec = AES.new(key, AES.MODE_CFB, iv,
                                          segment_size=128).decrypt(ct[:32])
                        elif mn == "OFB":
                            dec = AES.new(key, AES.MODE_OFB, iv).decrypt(ct[:32])
                        else:
                            dec = AES.new(
                                key, AES.MODE_CTR, nonce=b"",
                                initial_value=int.from_bytes(iv, "big")
                            ).decrypt(ct[:32])
                    except Exception:
                        continue
                    if dec[:8] == GOOD:
                        print("★★ 头命中 %-10s %-16s %-12s @%#x  %r"
                              % (kn, ivn, mn, ds, dec[:24]))
                        hits += 1
                    else:
                        for off in range(0, 8):
                            try:
                                d = zlib.decompressobj(15).decompress(dec[off:])
                                if len(d) > 200:
                                    print("★ zlib %s %s %s @%#x -> %d"
                                          % (kn, ivn, mn, ds, len(d)))
                                    hits += 1
                            except Exception:
                                pass
    print("\n命中 %d" % hits)


if __name__ == "__main__":
    main()
