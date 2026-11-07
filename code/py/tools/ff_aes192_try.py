#!/usr/bin/env python3
"""精确验证：RSA 解出的 40 字节 → AES-192 前 24 字节 → 试各种模式与数据偏移。"""
import json
import math
import sys
from collections import Counter

from Crypto.Cipher import AES

KW = [b"version", b"catinfo", b"gametype", b"playlist", b"menu", b"ui_mp",
      b"self.", b"function", b"name ", b"GSC"]


def ent(d):
    if not d:
        return 0
    c = Counter(d)
    n = len(d)
    return -sum((v / n) * math.log(v / n, 2) for v in c.values())


def score(d):
    s = 0
    if d[:2] in (b"\x78\x9c", b"\x78\x01", b"\x78\xda", b"\x1f\x8b"):
        s += 2000
    pr = sum(1 for c in d if 32 <= c < 127 or c in (9, 10, 13))
    s += pr * 3
    for k in KW:
        if k in d[:400]:
            s += 800
    e = ent(d[:256])
    if e < 6.0:
        s += int((7.5 - e) * 120)
    return s


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
    print("keymat(%d) @%#x: %s" % (len(keymat), keyoff, keymat.hex()))

    data0 = keyoff + ksz
    print("data0 = %#x, 数据长度 %d" % (data0, len(b) - data0))

    best = []
    for kl in (16, 24, 32):
        key = keymat[:kl]
        for dstart in (data0, data0 + 64, data0 + 32, data0 + 16):
            if dstart + 64 > len(b):
                continue
            ct = b[dstart:dstart + 128]
            trials = [("ECB", AES.new(key, AES.MODE_ECB).decrypt(
                ct[:(len(ct) // 16) * 16]))]
            for ivn, iv in (("zero", b"\0" * 16),
                            ("mat0", keymat[:16]),
                            ("mat24", keymat[24:40].ljust(16, b"\0"))):
                trials.append(("CBC-" + ivn,
                               AES.new(key, AES.MODE_CBC, iv).decrypt(
                                   ct[:(len(ct) // 16) * 16])))
                trials.append(("CFB-" + ivn,
                               AES.new(key, AES.MODE_CFB, iv,
                                       segment_size=128).decrypt(ct[:16])))
                trials.append(("OFB-" + ivn,
                               AES.new(key, AES.MODE_OFB, iv).decrypt(ct[:16])))
            for mode, dec in trials:
                s = score(dec)
                best.append((s, kl, mode, dstart, dec[:48]))

    best.sort(reverse=True)
    print("\n前 10：")
    for s, kl, mode, ds, dec in best[:10]:
        print("  %-5d keylen=%d %-10s @%#-7x %s" % (s, kl, mode, ds,
                                                    dec[:40].hex(" ")))
        print("        %r" % dec[:40])


if __name__ == "__main__":
    main()
