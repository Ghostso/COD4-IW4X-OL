#!/usr/bin/env python3
"""穷举：40 字节密钥材料 × (16/24/32 字节) × (ECB/CBC/CFB/OFB/CTR) × 多个数据起点，
找出能产生可识别明文（zlib 头 / ASCII / 低熵）的组合。
"""
import json
import struct
import sys

from Crypto.Cipher import AES


def load_key(p=r"_byte_papers\rsa_private_key.json"):
    d = json.load(open(p, encoding="utf-8"))
    return int(d["n"]), int(d["d"])


def rsa_block(b, off, n, d, k):
    m = pow(int.from_bytes(b[off:off + k], "big"), d, n)
    raw = m.to_bytes(k, "big")
    if raw[0] != 0 or raw[1] != 2:
        return None
    z = raw.find(b"\x00", 2)
    return raw[z + 1:] if z > 10 else None


def looks_good(d):
    """评分：zlib 头 / 高可打印 / 低熵"""
    score = 0
    if d[:2] in (b"\x78\x9c", b"\x78\x01", b"\x78\xda"):
        score += 100
    if d[:2] == b"\x1f\x8b":
        score += 100
    pr = sum(1 for c in d[:64] if 32 <= c < 127 or c in (9, 10, 13))
    score += pr
    if d[:4] == b"\x00\x00\x00\x00":
        score += 10
    return score


def main():
    path = sys.argv[1]
    n, d = load_key()
    k = (n.bit_length() + 7) // 8
    b = open(path, "rb").read()
    keymat = None
    for off in range(0, min(0x2000, len(b) - k)):
        km = rsa_block(b, off, n, d, k)
        if km:
            keymat, keyoff = km, off
            break
    if not keymat:
        print("no rsa")
        return
    data_start0 = keyoff + k
    print("keymat(%d): %s" % (len(keymat), keymat.hex()))
    print("data_start0 = %#x" % data_start0)

    best = []
    for klen in (16, 24, 32):
        for keyoff_in_mat in (0, 8, 16):
            if keyoff_in_mat + klen > len(keymat):
                continue
            key = keymat[keyoff_in_mat:keyoff_in_mat + klen]
            for dstart in (data_start0, data_start0 + 4,
                           data_start0 + 8, data_start0 + 16,
                           data_start0 + 24):
                if dstart + 32 > len(b):
                    continue
                ct = b[dstart:dstart + 32]
                # ECB
                try:
                    dec = AES.new(key, AES.MODE_ECB).decrypt(ct)
                    s = looks_good(dec)
                    if s >= 20:
                        best.append((s, "ECB", klen, keyoff_in_mat,
                                     dstart, dec[:32]))
                except Exception:
                    pass
                # CBC with zero IV and with first block as IV
                for ivname, iv in (("zero", b"\x00" * 16),):
                    try:
                        dec = AES.new(key, AES.MODE_CBC, iv).decrypt(ct)
                        s = looks_good(dec)
                        if s >= 20:
                            best.append((s, "CBC/" + ivname, klen,
                                         keyoff_in_mat, dstart, dec[:32]))
                    except Exception:
                        pass
                # CFB8 / CFB128
                for mode, mn in ((AES.MODE_CFB, "CFB"),
                                 (AES.MODE_OFB, "OFB")):
                    try:
                        dec = AES.new(key, mode, b"\x00" * 16,
                                      segment_size=128).decrypt(ct)
                        s = looks_good(dec)
                        if s >= 20:
                            best.append((s, mn, klen, keyoff_in_mat,
                                         dstart, dec[:32]))
                    except Exception:
                        pass

    best.sort(reverse=True)
    print("\n候选（按评分）:")
    for s, mode, kl, ko, ds, dec in best[:12]:
        print("  score=%-3d %-8s keylen=%-2d key@%-2d data@%#-6x %s"
              % (s, mode, kl, ko, ds, dec.hex(" ")))
    if not best:
        print("  无候选")


if __name__ == "__main__":
    main()
