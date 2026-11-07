#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""codol_ff_decrypt.py -- CODOL (使命召唤OL) fastfile decryption, LAYER 1.

Every claim below was re-verified from the raw .ff bytes on 2026-10-02.
Nothing here is copied from prior prose.

LAYOUT (verified byte-for-byte on 10 real files in `COD OL\\main\\`)
--------------------------------------------------------------------
    0x000  8   magic  'IWff0100'   (ASCII, plaintext, identical in all files)
    0x008  4   u32 version        (= 461 / 0x1CD for CODOL)
    0x00C  1   u8  language       (= 1)
    0x00D  4   u32 filetime_hi
    0x011  4   u32 filetime_lo
    ------------------------------------------------ 21 bytes = XFileHeader
    0x015  256 RSA-2048 PKCS#1 v1.5 encrypted key blob
    ------------------------------------------------ 0x115 body start
    0x115  ..  AES-192-CTR ciphertext

KEY RECOVERY
------------
The RSA private key is the *same* 1191-byte PKCS#1 DER blob that IW4X ships
as `FastFiles::ZoneKey` in Components/Modules/FastFiles.cpp.  CODOL reuses it.
All 10 observed CODOL zones share ONE derived AES key:
    key = da135e91c7981459a13ddc2aed3050ae6dd9a7ce619bb6c5   (24 bytes = AES-192)
    iv  = per-file, first 16 bytes of the RSA payload

CTR MODE
--------
libtomcrypt `ctr_start` / `ctr_decrypt`: the whole 16-byte counter block is
incremented LITTLE-ENDIAN, initial counter value == IV.  Confirmed because
raw[0x11D:0x121] differs per file yet decrypts to 00 00 00 00 in every file.

LAYER 1 RESULT
--------------
The body decrypts to an 'IWffs100' container:

    0x000  'IWffs100'     (plaintext magic)
    0x008  u32 = 0
    0x00C  16 bytes
    0x01C  ... padding ...
    0x120  12 bytes  per-zone metadata
    0x12C  zone name, ASCII, NUL-padded to 16 bytes   <-- PLAINTEXT
    0x13C  16 zero bytes
    0x14C  opaque stream (LAYER 2 - see notes at bottom)

>>> LAYER 2 STATUS: OPEN.  See `LAYER2_NOTES.md`.  <<<

Usage:
    python -X utf8 codol_ff_decrypt.py <in.ff|dir> [--out OUTDIR] [--json]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import struct
import sys

from Crypto.Cipher import AES

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, "..", ".."))

DER_FILE = os.path.join(PROJECT, "CODOLServer", "_mainline", "zonekey_der.hex")
IW4X_CPP = os.path.join(
    PROJECT, "IW4X", "Client核心代码", "iw4x-client", "src",
    "Components", "Modules", "FastFiles.cpp")

XFILE_HEADER_SIZE = 21          # magic8 + version4 + lang1 + filetime8
RSA_OFF = 0x15
RSA_LEN = 256
BODY_OFF = RSA_OFF + RSA_LEN    # 0x115


# ---------------------------------------------------------------- key material
def _load_der() -> bytes:
    """Return the 1191-byte PKCS#1 RSAPrivateKey DER blob."""
    if os.path.exists(DER_FILE):
        return bytes.fromhex(
            open(DER_FILE, encoding="ascii").read().strip())
    if os.path.exists(IW4X_CPP):
        import re
        src = open(IW4X_CPP, encoding="utf-8", errors="replace").read()
        m = src.index("ZoneKey[1191]")
        end = src.index("};", m)
        vals = re.findall(r"0x([0-9A-Fa-f]{2})", src[m:end])
        return bytes(int(v, 16) for v in vals)
    raise SystemExit("cannot locate ZoneKey (missing %s and %s)"
                     % (DER_FILE, IW4X_CPP))


def _der_section(blob: bytes) -> bytes:
    """Strip the outer SEQUENCE tag/length, return the inner body."""
    i = 1
    if blob[i] & 0x80:
        n = blob[i] & 0x7F
        i += 1 + n
    else:
        i += 1
    return blob[i:]


def _der_ints(blob: bytes):
    """Parse the 9 INTEGERs of an RSAPrivateKey in order."""
    body = _der_section(blob)
    out, i = [], 0
    while i < len(body):
        if body[i] != 0x02:
            raise SystemExit("DER: INTEGER expected at %d" % i)
        i += 1
        if body[i] & 0x80:
            n = body[i] & 0x7F
            i += 1
            ln = int.from_bytes(body[i:i + n], "big")
            i += n
        else:
            ln = body[i]
            i += 1
        out.append(int.from_bytes(body[i:i + ln], "big"))
        i += ln
    return out


def private_key():
    """Return (n, d) from the embedded ZoneKey."""
    der = _load_der()
    if len(der) != 1191:
        raise SystemExit("ZoneKey DER is %d bytes, expected 1191" % len(der))
    _, n, e, d, p, q, _dp, _dq, _qinv = _der_ints(der)
    if n != p * q:
        raise SystemExit("ZoneKey n != p*q  (DER parse is wrong)")
    return n, d


def rsa_unwrap(n: int, d: int, block: bytes):
    """PKCS#1 v1.5 decrypt; return the payload or None."""
    kl = (n.bit_length() + 7) // 8
    if len(block) != kl:
        return None
    c = int.from_bytes(block, "big")
    if c >= n:
        return None
    m = pow(c, d, n).to_bytes(kl, "big")
    if m[0] != 0x00 or m[1] != 0x02:
        return None
    cut = m.find(b"\x00", 2)
    return None if cut < 0 else m[cut + 1:]


# ------------------------------------------------------------------ ctr mode
def aes_ctr(data: bytes, key: bytes, iv: bytes) -> bytes:
    """libtomcrypt-compatible CTR: little-endian counter increment."""
    aes = AES.new(key, AES.MODE_ECB)
    out = bytearray(len(data))
    ctr = bytearray(iv)
    for off in range(0, len(data), 16):
        ks = aes.encrypt(bytes(ctr))
        for i, b in enumerate(data[off:off + 16]):
            out[off + i] = b ^ ks[i]
        for x in range(16):
            ctr[x] = (ctr[x] + 1) & 0xFF
            if ctr[x]:
                break
    return bytes(out)


# ------------------------------------------------------------------ layer 1
def recover_key(raw: bytes):
    """Return (key24, iv16) for a raw .ff file."""
    if raw[:4] != b"IWff":
        raise SystemExit("not an IWff file: %r" % raw[:8])
    n, d = private_key()
    payload = rsa_unwrap(n, d, raw[RSA_OFF:RSA_OFF + RSA_LEN])
    if payload is None:
        raise SystemExit("RSA block did not decrypt to PKCS#1 v1.5")
    if len(payload) != 40:
        raise SystemExit("unexpected key payload length %d" % len(payload))
    return bytes(payload[:24]), bytes(payload[24:40])


def decrypt_layer1(path: str) -> dict:
    raw = open(path, "rb").read()
    key, iv = recover_key(raw)
    plain = aes_ctr(raw[BODY_OFF:], key, iv)
    return {
        "path": path,
        "name": os.path.basename(path),
        "cipher_size": len(raw),
        "plain_size": len(plain),
        "magic": raw[:8].decode("ascii", "replace"),
        "version": struct.unpack_from("<I", raw, 8)[0],
        "language": raw[12],
        "filetime_hi": struct.unpack_from("<I", raw, 13)[0],
        "filetime_lo": struct.unpack_from("<I", raw, 17)[0],
        "key": key,
        "iv": iv,
        "plain": plain,
    }


def parse_zone_header(plain: bytes):
    """Best-effort structural parse of the IWffs100 container.

    Verified on 10/10 files: zone name sits at 0x12C, NUL-padded,
    followed by 16 zero bytes and then the opaque stream at 0x14C.
    """
    out = {}
    if plain[:8] != b"IWffs100":
        return out
    out["inner_magic"] = "IWffs100"
    out["inner_u32"] = struct.unpack_from("<I", plain, 8)[0]
    try:
        nul = plain.index(b"\x00", 0x12C)
        name = plain[0x12C:nul]
        if 1 <= len(name) <= 128 and all(32 <= c < 127 for c in name):
            out["zone_name"] = name.decode("ascii")
            out["zone_name_off"] = 0x12C
    except ValueError:
        pass
    return out


# --------------------------------------------------------------------- main
def iter_inputs(target: str):
    if os.path.isdir(target):
        for p in sorted(glob.glob(os.path.join(target, "*.ff"))):
            yield p
    else:
        yield target


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--out")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    results = []
    for path in iter_inputs(args.input):
        try:
            info = decrypt_layer1(path)
        except SystemExit as exc:
            print("SKIP %-40s %s" % (os.path.basename(path), exc))
            continue
        hdr = parse_zone_header(info["plain"])
        rec = {
            "file": info["name"],
            "cipher_size": info["cipher_size"],
            "plain_size": info["plain_size"],
            "magic": info["magic"],
            "version": info["version"],
            "aes_key": info["key"].hex(),
            "iv": info["iv"].hex(),
        }
        rec.update(hdr)
        results.append(rec)

        if args.out:
            os.makedirs(args.out, exist_ok=True)
            dst = os.path.join(args.out, info["name"] + ".layer1.bin")
            with open(dst, "wb") as fh:
                fh.write(info["plain"])

        if not args.json:
            print("%-34s size=%-9d key=%s iv=%s" % (
                info["name"], info["plain_size"],
                info["key"].hex(), info["iv"].hex()))
            if "zone_name" in hdr:
                print("    zone_name@0x%x = %r" % (
                    hdr["zone_name_off"], hdr["zone_name"]))

    if args.json:
        print(json.dumps(results, indent=1, ensure_ascii=False))
    else:
        print()
        print("decrypted %d file(s)" % len(results))
        keys = {r["aes_key"] for r in results}
        print("distinct AES keys: %d  -> %s" % (len(keys), ", ".join(keys)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
