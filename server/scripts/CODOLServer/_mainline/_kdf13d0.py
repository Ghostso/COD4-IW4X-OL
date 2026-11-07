"""Offline reconstruction of the 0xBA13D0 KDF.

Structure recovered from the disassembly:

    counter = 1
    seed    = 0x190-byte buffer holding: u32 0 | <input bytes, len I> | 0x01
    repeat:
        ctx = MD(key = <first arg>, len = <second arg>)   # 0xC73800
        ctx.skip(seed_len)                                # 0xC73760
        block20 = ctx.final()                             # 0xC737A0
        append block20
        counter += 1
        seed = u32 0 | appended_so_far | counter_byte
    until len(appended) >= target_len

The digest is HMAC-SHA1 whose key is supplied by the caller (20 bytes for the
BDDATA derivation).  This script lets us test candidate key/message layouts
against a captured 0x48-byte or 0x10-byte output.
"""
from __future__ import annotations

import hashlib
import hmac
import sys


def kdf(key: bytes, seed_input: bytes, target_len: int,
        max_iter: int = 64) -> bytes:
    out = bytearray()
    counter = 1
    while len(out) < target_len and counter <= max_iter:
        message = b"\x00\x00\x00\x00" + bytes(out) + bytes([counter & 0xFF])
        digest = hmac.new(key, message, hashlib.sha1).digest()
        out.extend(digest)
        counter += 1
    return bytes(out[:target_len])


def kdf_plain(key: bytes, seed_input: bytes, target_len: int,
              max_iter: int = 64) -> bytes:
    """Variant: no HMAC, plain SHA1 over the seed buffer."""
    out = bytearray()
    counter = 1
    while len(out) < target_len and counter <= max_iter:
        message = b"\x00\x00\x00\x00" + bytes(out) + bytes([counter & 0xFF])
        out.extend(hashlib.sha1(message).digest())
        counter += 1
    return bytes(out[:target_len])


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: _kdf13d0.py <key-hex> <seed-hex> [len]")
        return 2
    key = bytes.fromhex(sys.argv[1])
    seed = bytes.fromhex(sys.argv[2])
    target = int(sys.argv[3]) if len(sys.argv) > 3 else 0x48
    print("key ", key.hex())
    print("seed", seed.hex())
    print("hmac ", kdf(key, seed, target).hex())
    print("plain", kdf_plain(key, seed, target).hex())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
