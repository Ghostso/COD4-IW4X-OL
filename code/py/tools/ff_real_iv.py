#!/usr/bin/env python3
"""E(IV) 前 8 字节匹配、后 8 字节不匹配 => IV 的后 8 字节被覆盖。
从 E(IV) actual 反推真实 IV:  IV = D(E(IV)_actual)
然后用这个真实 IV 解全文。
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
    key = mat[:24]
    body = b[koff + ksz:]

    # known: P0 = "IWffs100" + 8 zeros ; C0 = body[:16]
    # C0 = P0 ^ E(IV)  =>  E(IV) = P0 ^ C0
    p0 = b"IWffs100" + b"\x00" * 8
    eiv = bytes(a ^ c for a, c in zip(p0, body[:16]))
    ecb = AES.new(key, AES.MODE_ECB)
    real_iv = ecb.decrypt(eiv)
    print("real IV =", real_iv.hex())
    print("mat[24:40] =", mat[24:40].hex())
    print("diff =", bytes(a ^ c for a, c in
                          zip(real_iv, mat[24:40])).hex())
    print()

    for mn in ("CFB", "OFB", "CTR"):
        try:
            if mn == "CFB":
                pt = AES.new(key, AES.MODE_CFB, real_iv,
                             segment_size=128).decrypt(body[:4096])
            elif mn == "OFB":
                pt = AES.new(key, AES.MODE_OFB, real_iv).decrypt(body[:4096])
            else:
                pt = AES.new(key, AES.MODE_CTR, nonce=b"",
                             initial_value=int.from_bytes(real_iv, "big")
                             ).decrypt(body[:4096])
        except Exception:
            continue
        pr = sum(1 for c in pt[:512] if 32 <= c < 127 or c in (9, 10, 13))
        print("[%s] printable=%d/512" % (mn, pr))
        print("   head:", pt[:64])
        print("   repr:", repr(pt[:48]))


if __name__ == "__main__":
    main()
