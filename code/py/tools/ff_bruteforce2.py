#!/usr/bin/env python3
"""全面穷举 AES 参数：密钥来源(多个子串)、长度、模式、IV、数据偏移。
评分依据：可打印率、zlib/gzip 头、熵、是否出现已知 GSC/菜单关键字。
"""
import json
import math
import sys
from collections import Counter

from Crypto.Cipher import AES

KW = [b"version", b"catinfo", b"gametype", b"playlist", b"menu", b"ui_mp",
      b"GSC", b"self", b"main", b"function", b"name", b"{"]


def ent(d):
    if not d:
        return 0
    c = Counter(d)
    n = len(d)
    return -sum((v / n) * math.log(v / n, 2) for v in c.values())


def score(d):
    s = 0
    if d[:2] in (b"\x78\x9c", b"\x78\x01", b"\x78\xda", b"\x1f\x8b"):
        s += 500
    pr = sum(1 for c in d if 32 <= c < 127 or c in (9, 10, 13))
    s += pr * 2
    for k in KW:
        if k in d[:512]:
            s += 300
    e = ent(d[:256])
    if e < 6.5:
        s += int((7.5 - e) * 100)
    return s


def main():
    ff = sys.argv[1]
    keyf = r"_byte_papers\rsa_private_key.json"
    kd = json.load(open(keyf, encoding="utf-8"))
    n, dpriv = int(kd["n"]), int(kd["d"])
    ksz = (n.bit_length() + 7) // 8
    b = open(ff, "rb").read()

    # 解 RSA
    keymat = None
    for off in range(0, min(0x2000, len(b) - ksz)):
        m = pow(int.from_bytes(b[off:off + ksz], "big"), dpriv, n)
        raw = m.to_bytes(ksz, "big")
        if raw[0] == 0 and raw[1] == 2:
            z = raw.find(b"\x00", 2)
            if z > 10:
                keymat, keyoff = raw[z + 1:], off
                break
    print("keymat(%d) @%#x: %s" % (len(keymat), keyoff, keymat.hex()))
    tail64 = b[-64:]
    print("tail64: %s" % tail64.hex())

    keys = []
    for base_name, base in (("keymat", keymat), ("tail64", tail64)):
        for ko in range(0, max(1, len(base) - 15)):
            for kl in (16, 24, 32):
                if ko + kl <= len(base):
                    keys.append(("%s[%d:%d]" % (base_name, ko, ko + kl),
                                 base[ko:ko + kl]))
        for kl in (16, 24, 32):
            if kl <= len(base):
                keys.append(("%s[:%d]" % (base_name, kl), base[:kl]))

    best = []
    data0 = keyoff + ksz
    starts = [data0, data0 + 64, data0 + 4, data0 - 32,
              len(b) - 64 - 8192, len(b) - 16 - 8192]
    for kname, key in keys:
        for dstart in starts:
            if dstart < 0 or dstart + 32 > len(b):
                continue
            ct = b[dstart:dstart + 64]
            trials = []
            try:
                trials.append(("ECB", AES.new(key, AES.MODE_ECB).decrypt(ct)))
            except Exception:
                pass
            for ivn, iv in (("zero", b"\0" * 16), ("tail", tail64[:16])):
                try:
                    trials.append(("CBC-" + ivn,
                                   AES.new(key, AES.MODE_CBC, iv).decrypt(ct)))
                except Exception:
                    pass
                try:
                    trials.append(("CFB-" + ivn,
                                   AES.new(key, AES.MODE_CFB, iv,
                                           segment_size=128).decrypt(ct)))
                except Exception:
                    pass
                try:
                    trials.append(("OFB-" + ivn,
                                   AES.new(key, AES.MODE_OFB, iv).decrypt(ct)))
                except Exception:
                    pass
            for mode, dec in trials:
                s = score(dec)
                if s > 120:
                    best.append((s, kname, mode, dstart, dec[:64]))

    best.sort(reverse=True)
    print("\n候选 %d 个，前 12：" % len(best))
    for s, kn, mode, ds, dec in best[:12]:
        print("  %-5d %-22s %-10s @%#-7x %s" % (s, kn, mode, ds, dec[:48].hex(" ")))
        print("        %r" % dec[:48])


if __name__ == "__main__":
    main()
