# -*- coding: utf-8 -*-
"""codol_ff_unpack.py -- CODOL fastfile LAYER 2 unpack (per-block CTR + zlib).

Layer 1 (RSA unwrap + block0) comes from _PLAINTEXT_PROJECT/tools/codol_ff_decrypt.py.
This adds LAYER 2, per ol-mod's packer
(_e1_regression/ol-mod-olfinal/tools/reverse/OlfinalFastfile.py :: unpack_zone):

    block0        = CTR(key_material[24:])
    per section i:  digest_i = block0[336 + i*32][:32]
                    level2   = CTR(block, key, digest_i[:16])   # 256 x 32B SHA-256
    per data block: CTR(block, key, sha256_of_block[:16])
    concat -> zlib.decompress -> zone

  >>> NOT a continuous CTR stream: each 0x2000 block carries its own IV. <<<

Usage:  python -X utf8 tools\\codol_ff_unpack.py <in.ff> <out.zone> [--name ZONE]
"""
import argparse, hashlib, os, sys, zlib

DEC = r"D:\BaiduNetdiskDownload\使命召唤OL\_PLAINTEXT_PROJECT\tools"
sys.path.insert(0, DEC)
import codol_ff_decrypt as D

BLOCK = 0x2000
OUTER = 0x115
L1_OFF = 336
DATA_BLOCKS_PER_SECTION = 256


def unpack(path, out_path, expect_name=None):
    raw = open(path, "rb").read()
    key, iv = D.recover_key(raw)
    body = raw[OUTER:]

    def block_at(p):
        b = body[p:p + BLOCK]
        return b + b"\0" * (BLOCK - len(b))

    block0 = D.aes_ctr(block_at(0), key, iv)
    if block0[:8] != b"IWffs100":
        raise SystemExit("inner magic is not IWffs100")
    name = block0[300:332].split(b"\0")[0].decode("ascii", "replace")
    if expect_name and name != expect_name:
        raise SystemExit("zone name %r != expected %r" % (name, expect_name))

    out = bytearray(); pos, sec, stats = BLOCK, 0, []
    while pos < len(body):
        d1 = block0[L1_OFF + sec*32: L1_OFF + sec*32 + 32]
        enc = block_at(pos); pos += BLOCK
        l2 = D.aes_ctr(enc, key, d1[:16])
        n = 0
        while pos < len(body) and n < DATA_BLOCKS_PER_SECTION:
            d2 = l2[n*32:(n+1)*32]
            if d2 == b"\0"*32:
                break
            e = block_at(pos); pos += BLOCK
            b = D.aes_ctr(e, key, d2[:16])
            if hashlib.sha256(b).digest() != d2:
                break
            out.extend(b); n += 1
        stats.append(n); sec += 1
        if n == 0:
            break

    zone = zlib.decompress(bytes(out))
    open(out_path, "wb").write(zone)
    print("zone=%s key=%s iv=%s" % (name, key.hex(), iv.hex()))
    print("sections=%d blocks=%s" % (len(stats), stats))
    print("zone bytes=%d -> %s" % (len(zone), out_path))
    return name, zone


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("infile"); ap.add_argument("outfile")
    ap.add_argument("--name", default=None)
    a = ap.parse_args()
    unpack(a.infile, a.outfile, a.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
