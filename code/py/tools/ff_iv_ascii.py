#!/usr/bin/env python3
"""ASCII-only output version."""
import json
import sys

from Crypto.Cipher import AES


def main():
    ff = sys.argv[1]
    kd = json.load(open(r"_byte_papers\rsa_private_key.json", encoding="utf-8"))
    n, dp = int(kd["n"]), int(kd["d"])
    ksz = (n.bit_length() + 7) // 8
    b = open(ff, "rb").read()
    mat = None
    for off in range(0, min(0x2000, len(b) - ksz)):
        m = pow(int.from_bytes(b[off:off + ksz], "big"), dp, n)
        raw = m.to_bytes(ksz, "big")
        if raw[0] == 0 and raw[1] == 2:
            z = raw.find(b"\x00", 2)
            if z > 10:
                mat, koff = raw[z + 1:], off
                break
    key, iv = mat[:24], mat[24:40]
    body = b[koff + ksz:]
    ecb = AES.new(key, AES.MODE_ECB)
    ct = body[:64]

    p0 = b"IWffs100" + b"\x00" * 8
    eiv_actual = bytes(a ^ c for a, c in zip(p0, ct[:16]))
    eiv_calc = ecb.encrypt(iv)
    print("E(IV) actual  =", eiv_actual.hex())
    print("E(IV) from iv =", eiv_calc.hex())
    print("MATCH =", eiv_actual == eiv_calc)
    print()

    # Try: what IV does block 1 need?
    # C1 = P1 ^ E(IV1). We don't know P1. But if P1 starts with a known
    # pattern? Try treating P1 as "  " or checking if C1^C0 looks sane.
    print("block0 ct =", ct[:16].hex())
    print("block1 ct =", ct[16:32].hex())
    print("block0 pt =", p0.decode("latin1", "replace"))
    print()

    # Hypothesis: IV for each block = previous block's PLAINTEXT
    for name, cand in (("C0", ct[:16]), ("P0", p0), ("IV", iv)):
        e = ecb.encrypt(cand)
        p1 = bytes(a ^ c for a, c in zip(e, ct[16:32]))
        printable = sum(1 for c in p1 if 32 <= c < 127)
        print("IV1=%-4s -> P1 = %r  (printable=%d/16)" % (
            name, p1, printable))


if __name__ == "__main__":
    main()
