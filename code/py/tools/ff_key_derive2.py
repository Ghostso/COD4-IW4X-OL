#!/usr/bin/env python3
"""按修正后的参数映射重新尝试：
   cipher_setup(idx, key=[ebp-0x14], keylen=24, ...)
   => key 来自 [ebp-0x14]，即 RSA 输出的前/某 24 字节被复制进去
但仍需确认 [ebp-0x14] 内容。既然 rsa 输出在 [ebp-0x2c]，
则 [ebp-0x14] 可能是 rsa 输出的一个子区间，或用 sha256(rsa输出) 派生。

本脚本穷举所有合理派生：直接切片 / sha256 / sha256 截断 / 拼接。
"""
import hashlib
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
    ct = b[koff + ksz:]
    print("mat(%d)=%s" % (len(mat), mat.hex()))
    print("ct@%#x len=%d" % (koff + ksz, len(ct)))

    cands = {}
    # 1) 直接切片
    for a in range(0, len(mat) - 15):
        for L in (16, 24, 32):
            if a + L <= len(mat):
                cands["mat[%d:%d]" % (a, a + L)] = mat[a:a + L]
    # 2) sha256 派生
    for src_name, src in (("mat", mat), ("mat[:24]", mat[:24]),
                          ("mat[:32]", mat[:32]), ("mat[24:]", mat[24:])):
        h = hashlib.sha256(src).digest()
        for L in (16, 24, 32):
            cands["sha256(%s)[:%d]" % (src_name, L)] = h[:L]
    # 3) md5
    for src_name, src in (("mat", mat), ("mat[:24]", mat[:24])):
        d = hashlib.md5(src).digest()
        for L in (16, 24):
            cands["md5(%s)[:%d]" % (src_name, L)] = (d * 2)[:L]

    ivs = {"zero": b"\0" * 16}
    for a in range(0, max(1, len(mat) - 15)):
        ivs["mat[%d:%d]" % (a, a + 16)] = mat[a:a + 16]
    ivs["ct[-16:]"] = ct[-16:]
    ivs["ct[8176:8192]"] = ct[8176:8192]
    ivs["ct[:16]"] = ct[:16]

    hits = []
    for kn, key in cands.items():
        for ivn, iv in ivs.items():
            for mn in ("CFB", "OFB", "CTR", "CBC"):
                try:
                    if mn == "CFB":
                        pt = AES.new(key, AES.MODE_CFB, iv,
                                     segment_size=128).decrypt(ct[:8192])
                    elif mn == "OFB":
                        pt = AES.new(key, AES.MODE_OFB, iv).decrypt(ct[:8192])
                    elif mn == "CTR":
                        pt = AES.new(key, AES.MODE_CTR, nonce=b"",
                                     initial_value=int.from_bytes(iv, "big")
                                     ).decrypt(ct[:8192])
                    else:
                        pt = AES.new(key, AES.MODE_CBC, iv).decrypt(ct[:8192])
                except Exception:
                    continue
                if pt[:9] != b"IWffs100":
                    continue
                # 检查 16 字节之后是不是也有意义
                pr = sum(1 for c in pt[16:272]
                         if 32 <= c < 127 or c in (9, 10, 13))
                hits.append((pr, kn, ivn, mn, pt[:32]))
                for i in range(0, 64):
                    try:
                        d = zlib.decompressobj().decompress(pt[i:])
                        if len(d) > 500:
                            print("★★ zlib  %s %s %s @%d -> %d"
                                  % (kn, ivn, mn, i, len(d)))
                            print("   %r" % d[:200])
                    except Exception:
                        pass
    hits.sort(reverse=True)
    print("\n头匹配且正文可打印性排序：")
    for pr, kn, ivn, mn, head in hits[:10]:
        print("  printable=%3d  %-22s %-16s %-4s %r" % (pr, kn, ivn, mn, head))


if __name__ == "__main__":
    main()
