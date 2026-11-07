#!/usr/bin/env python3
"""用已确定的参数解密整个 .ff：AES-192，key=RSA材料前24B，IV=材料[24:40]，
流模式（CFB128 / OFB），数据起点 = RSA 块之后。输出明文并通过校验判定模式。
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
    if not keymat:
        print("no key")
        return
    key = keymat[:24]
    iv = keymat[24:40]
    data0 = keyoff + ksz
    ct = b[data0:]
    print("keymat: %s" % keymat.hex())
    print("key(24): %s" % key.hex())
    print("iv(16) : %s" % iv.hex())
    print("ct len : %d  (data0=%#x)" % (len(ct), data0))

    # 前 16 字节是明文头（IWffs100 + 计数），密文从 +16 开始
    HDR = 16
    print("\n明文头: %r" % ct[:HDR])
    ct_enc = ct[HDR:]
    for mode_name in ("CFB", "OFB", "CTR"):
        if mode_name == "CFB":
            cipher = AES.new(key, AES.MODE_CFB, iv, segment_size=128)
        elif mode_name == "OFB":
            cipher = AES.new(key, AES.MODE_OFB, iv)
        else:
            cipher = AES.new(key, AES.MODE_CTR,
                             nonce=b"", initial_value=int.from_bytes(iv, "big"))
        pt = cipher.decrypt(ct_enc)
        print("\n===== %s  (从 +16 起) =====" % mode_name)
        print("前 48 repr: %r" % pt[:48])
        print("前 48 hex : %s" % pt[:48].hex(" "))
        print("可打印率: %.0f%%" % (100.0 * sum(
            1 for c in pt[:256] if 32 <= c < 127 or c in (9, 10, 13)) / 256))
        for off in range(0, 16):
            for wbits in (15, -15, 31):
                try:
                    dec = zlib.decompressobj(wbits).decompress(pt[off:])
                    if len(dec) > 500:
                        print("★ zlib ok off=%d wbits=%d -> %d"
                              % (off, wbits, len(dec)))
                        print("  %r" % dec[:200])
                        if out:
                            open(out, "wb").write(pt)
                            open(out + ".z", "wb").write(dec)
                        break
                except Exception:
                    pass
            else:
                continue
            break
        print("\n===== %s =====" % mode_name)
        print("前 64: %s" % pt[:64].hex(" "))
        print("前 64 repr: %r" % pt[:64])
        # 头是 IWffs100
        if pt[:9] != b"IWffs100":
            print("头部不匹配，跳过")
            continue
        print("头: %r" % pt[:32])
        # 尝试 zlib 解压（可能在偏移处）
        for off in range(0, 64):
            for wbits in (15, -15, 31):
                try:
                    dec = zlib.decompressobj(wbits).decompress(pt[off:])
                    if len(dec) > 1000:
                        print("★ zlib 解压成功 offset=%d wbits=%d -> %d 字节"
                              % (off, wbits, len(dec)))
                        print("  前 200: %r" % dec[:200])
                        if out:
                            open(out, "wb").write(pt)
                            open(out + ".z", "wb").write(dec)
                            print("  已写出 %s 和 %s.z" % (out, out))
                        break
                except Exception:
                    pass
            else:
                continue
            break

        # 尾部 64 字节检查
        print("末尾 64: %s" % pt[-64:].hex(" "))
        h1 = pt[-64:-32]
        h2 = pt[-32:]
        body = pt[:-64]
        print("body sha256 : %s" % hashlib.sha256(body).hexdigest())
        print("tail[-64:-32]: %s" % h1.hex())
        print("tail[-32:]   : %s" % h2.hex())


if __name__ == "__main__":
    main()
