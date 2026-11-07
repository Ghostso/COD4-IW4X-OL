#!/usr/bin/env python3
"""分析块结构：块 0 用 IV0 解对了（头正确），求块 1 实际使用的 IV。

若块 0 的最后 16 字节密文是块 1 的 IV（CBC 链或"密文反馈"），
则可用它验证块 1 头部。
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
                keymat, keyoff = raw[z + 1:], off
                break
    key, iv = keymat[:24], keymat[24:40]
    ct = b[keyoff + ksz:]
    print("key=%s iv=%s ctlen=%d" % (key.hex(), iv.hex(), len(ct)))

    # 1) 块 0 用什么模式能解码出全明文？逐 16 字节检查
    print("\n[块0 前 96 字节，各模式解出]")
    for mn in ("CFB", "OFB", "CTR"):
        if mn == "CFB":
            o = AES.new(key, AES.MODE_CFB, iv, segment_size=128).decrypt(ct[:96])
        elif mn == "OFB":
            o = AES.new(key, AES.MODE_OFB, iv).decrypt(ct[:96])
        else:
            o = AES.new(key, AES.MODE_CTR, nonce=b"",
                        initial_value=int.from_bytes(iv, "big")).decrypt(ct[:96])
        print("  %s: %r" % (mn, o))

    # 2) 块 1 起点 = 8192。尝试用块0最后16密文字节作 IV
    blk1 = ct[8192:]
    cand_ivs = {
        "ct[8176:8192]": ct[8176:8192],
        "ct[8192-16:8192]": ct[8182 - 6:8192],
        "iv": iv,
        "ct[:16]": ct[:16],
    }
    print("\n[块1 头部（密文）] %s" % blk1[:16].hex(" "))
    for name, civ in cand_ivs.items():
        if len(civ) != 16:
            continue
        for mn in ("CFB", "OFB", "CTR"):
            try:
                if mn == "CFB":
                    o = AES.new(key, AES.MODE_CFB, civ,
                                segment_size=128).decrypt(blk1[:16])
                elif mn == "OFB":
                    o = AES.new(key, AES.MODE_OFB, civ).decrypt(blk1[:16])
                else:
                    o = AES.new(key, AES.MODE_CTR, nonce=b"",
                                initial_value=int.from_bytes(civ, "big")
                                ).decrypt(blk1[:16])
            except Exception:
                continue
            ok = b"IWff" in o or all(32 <= x < 127 or x in (9, 10) for x in o)
            print("  iv=%-16s %s -> %r %s" % (name, mn, o, "★" if ok else ""))


if __name__ == "__main__":
    main()
