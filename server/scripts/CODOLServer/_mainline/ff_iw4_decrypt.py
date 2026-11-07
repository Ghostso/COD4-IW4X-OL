#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ff_iw4_decrypt.py -- offline COD OL fastfile (IWff*) layer-1 decryptor.

Recovered chain (2026-09-30, static analysis + crypto verification):

    file layout
      0x00  XFileHeader (21 bytes): magic 'IWff0100' u64, version u32,
            language u8, filetime hi u32, filetime lo u32
      0x15  256-byte RSA-2048 PKCS#1 v1.5 encrypted AES key blob
      0x115 body = AES-CTR

    key recovery
      The RSA private key (PKCS#1 RSAPrivateKey, DER, 1191 bytes) is the
      *same* ZoneKey hardcoded in the IW4X client (FastFiles.cpp,
      FastFiles::ZoneKey).  The 256-byte blob decrypts as PKCS#1 v1.5
      (00 02 <padding> 00 <payload>); the 40-byte payload is:
          payload[0:24]   AES-192 key
          payload[24:40]  16-byte IV / initial CTR value
      Counter mode is libtomcrypt CTR: whole 16-byte block incremented
      little-endian, initial value == IV.

    layer-1 result
      Decrypting the body yields a container starting with the ASCII magic
      'IWffs100' followed by the internal zone name (e.g. 'mp_playlists',
      'code_post_gfx_mp').  This differs from the plain iw4 / IW4X stream
      (magic 'IWffu100' / 'IWff0100' then a zlib stream): COD OL uses the
      engine's own 'IWffs100' container.

    >>> LAYER 2 IS STILL OPEN <<<
      Post-CTR the payload is NOT zlib / raw-deflate / gzip / lzma / bz2,
      NOT AES-ECB/CBC (XOR of two distant 4 KiB windows stays at entropy
      7.96, so there is no repeated keystream), and not plaintext (no asset
      strings beyond the zone name).  Only the 12-byte head
      ('IWffs100' + 4 zero bytes) is low-entropy.  Treat layer 1 as
      confirmed and layer 2 as an unsolved transform.

Read-only: never touches a running process or the network.

Usage:
    python -X utf8 CODOLServer/_mainline/ff_iw4_decrypt.py <in.ff> [outdir] [--dump]
"""

from __future__ import annotations

import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, "..", ".."))
DER_FILE = os.path.join(HERE, "zonekey_der.hex")
IW4X_CPP = os.path.join(
    PROJECT, "IW4X", "Client核心代码", "iw4x-client", "src",
    "Components", "Modules", "FastFiles.cpp")

HEADER_SIZE = 21
RSA_BLOCK_OFF = 0x15
RSA_BLOCK_LEN = 256
BODY_OFF = RSA_BLOCK_OFF + RSA_BLOCK_LEN          # 0x115


def _load_der() -> bytes:
    if os.path.exists(DER_FILE):
        return bytes.fromhex(open(DER_FILE, encoding="ascii").read().strip())
    if os.path.exists(IW4X_CPP):
        import re
        src = open(IW4X_CPP, encoding="utf-8", errors="replace").read()
        m = src.index("ZoneKey[1191]")
        end = src.index("};", m)
        vals = re.findall(r"0x([0-9A-Fa-f]{2})", src[m:end])
        return bytes(int(v, 16) for v in vals)
    raise SystemExit("cannot locate the IW4X ZoneKey (missing %s)" % DER_FILE)


def _der_ints(blob: bytes):
    out = []
    i = 1
    if blob[i] & 0x80:
        n = blob[i] & 0x7F
        i += 1
        ln = int.from_bytes(blob[i:i + n], "big")
        i += n
    else:
        ln = blob[i]
        i += 1
    end = i + ln
    while i < end:
        if blob[i] != 0x02:
            raise SystemExit("DER: INTEGER expected at %d" % i)
        i += 1
        if blob[i] & 0x80:
            n = blob[i] & 0x7F
            i += 1
            l = int.from_bytes(blob[i:i + n], "big")
            i += n
        else:
            l = blob[i]
            i += 1
        out.append(int.from_bytes(blob[i:i + l], "big"))
        i += l
    return out


def private_key():
    der = _load_der()
    if len(der) != 1191:
        raise SystemExit("ZoneKey DER is %d bytes, expected 1191" % len(der))
    _, n, e, d, p, q, _dp, _dq, _qinv = _der_ints(der)
    if n != p * q:
        raise SystemExit("ZoneKey n != p*q")
    return n, d


def rsa_decrypt_key(n, d, block):
    kl = (n.bit_length() + 7) // 8
    c = int.from_bytes(block, "big")
    if c >= n:
        return None
    m = pow(c, d, n).to_bytes(kl, "big")
    if m[0] != 0 or m[1] != 2:
        return None
    cut = m.find(b"\x00", 2)
    return None if cut < 0 else m[cut + 1:]


def aes_ctr(data, key, iv):
    from Crypto.Cipher import AES
    aes = AES.new(key, AES.MODE_ECB)
    out = bytearray(len(data))
    ctr = bytearray(iv)
    for off in range(0, len(data), 16):
        ks = aes.encrypt(bytes(ctr))
        for i, b in enumerate(data[off:off + 16]):
            out[off + i] = b ^ ks[i]
        for x in range(16):                       # little-endian increment
            ctr[x] = (ctr[x] + 1) & 0xFF
            if ctr[x]:
                break
    return bytes(out)


def inner_zone(plain: bytes):
    """Return the embedded zone name of an 'IWffs100' container, if present.

    Two observed head shapes (8-byte magic + 4 bytes that are zero):
        'IWffs100' 00 00 00 00 <name> 00 ...
          -> name starts at 8
        'IWffs100' 00 00 00 00 <u8 len> <name> 00 ...
          -> one length byte precedes the name (seen on code_post_gfx_mp)
    """
    if plain[:8] != b"IWffs100":
        return None
    body = plain[8:]
    # skip up to 4 leading NUL bytes
    i = 0
    while i < 4 and i < len(body) and body[i] == 0:
        i += 1
    # optional single length byte
    if i < len(body) and body[i] == 0x00 and len(body) > i + 1:
        i += 1
    j = body.find(b"\x00", i)
    if j < 0 or not (2 <= j - i <= 128):
        return None
    cand = body[i:j]
    if all(32 <= c < 127 for c in cand):
        return cand
    return None




def decrypt_file(path: str):
    raw = open(path, "rb").read()
    if raw[:4] != b"IWff":
        return decrypt_embedded(path, raw)
    n, d = private_key()
    payload = rsa_decrypt_key(
        n, d, raw[RSA_BLOCK_OFF:RSA_BLOCK_OFF + RSA_BLOCK_LEN])
    if payload is None:
        raise SystemExit("RSA block did not decrypt to PKCS#1 v1.5")
    if len(payload) != 40:
        raise SystemExit("unexpected Key payload length %d" % len(payload))
    key, iv = bytes(payload[:24]), bytes(payload[24:40])
    plain = aes_ctr(raw[BODY_OFF:], key, iv)
    return {
        "path": path,
        "size": len(raw),
        "magic": raw[:8],
        "version": struct.unpack_from("<I", raw, 8)[0],
        "key": key,
        "iv": iv,
        "plain": plain,
    }


def decrypt_embedded(path: str, raw: bytes):
    """Handle an IIPS '.ifs' container that embeds 'IWff0100' fastfiles.

    The container is: 'nifs' header, name list, then one or more IWff
    blobs.  We decrypt the first embedded fastfile (zone packages normally
    carry a single zone).  Returns the same dict shape as decrypt_file.
    """
    off = raw.find(b"IWff0100")
    if off < 0:
        raise SystemExit("not an IWff fastfile and no embedded IWff: %r" % raw[:8])
    sub = raw[off:off + BODY_OFF + 64]
    n, d = private_key()
    payload = rsa_decrypt_key(n, d, sub[RSA_BLOCK_OFF:RSA_BLOCK_OFF + RSA_BLOCK_LEN])
    if payload is None or len(payload) != 40:
        raise SystemExit("embedded fastfile RSA block failed")
    key, iv = bytes(payload[:24]), bytes(payload[24:40])
    plain = aes_ctr(raw[off + BODY_OFF:], key, iv)
    return {
        "path": path,
        "size": len(raw),
        "magic": sub[:8],
        "version": struct.unpack_from("<I", sub, 8)[0],
        "key": key,
        "iv": iv,
        "plain": plain,
        "ifs_offset": off,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("outdir", nargs="?")
    ap.add_argument("--dump", action="store_true")
    args = ap.parse_args()
    info = decrypt_file(args.input)
    print("file        %s" % info["path"])
    print("size        %d" % info["size"])
    if "ifs_offset" in info:
        print("ifs offset  %#x" % info["ifs_offset"])
    print("magic       %r" % info["magic"])
    print("version     %d" % info["version"])
    print("AES key     %s" % info["key"].hex())
    print("IV          %s" % info["iv"].hex())
    print("plain[0:16] %r" % info["plain"][:16])
    name = inner_zone(info["plain"])
    if name is not None:
        print("inner zone  %r" % name)
    if args.outdir and args.dump:
        os.makedirs(args.outdir, exist_ok=True)
        dst = os.path.join(args.outdir, os.path.basename(args.input) + ".layer1.bin")
        with open(dst, "wb") as fh:
            fh.write(info["plain"])
        print("wrote       %s (%d bytes)" % (dst, len(info["plain"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
