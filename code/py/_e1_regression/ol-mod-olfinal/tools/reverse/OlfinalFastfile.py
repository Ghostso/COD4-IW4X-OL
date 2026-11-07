#!/usr/bin/env python3
"""Pack an inflated OLFinal zone body into the native encrypted .ff container.

The matching runtime must set OLMOD_ALLOW_UNSIGNED_FASTFILES=1. The plugin then
accepts only the RSA verdict; native header, version, zone-name, SHA-256 block,
AES-192 CTR and zlib checks remain active.
"""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import secrets
import sys
import zlib

try:
    from Crypto.Cipher import AES, PKCS1_v1_5
    from Crypto.Hash import SHA256
    from Crypto.PublicKey import RSA
    from Crypto.Signature import pkcs1_15
except ImportError as error:
    raise SystemExit("PyCryptodome is required: py -m pip install pycryptodome") from error


OUTER_MAGIC = b"IWff0100"
INNER_MAGIC = b"IWffs100"
VERSION = 461
OUTER_HEADER_SIZE = 0x115
BLOCK_SIZE = 0x2000
SIGNED_REGION_OFFSET = 300
SIGNED_REGION_SIZE = 7844
SIGNATURE_OFFSET = 44
SIGNATURE_SIZE = 256
ZONE_NAME_OFFSET = 300
ZONE_NAME_SIZE = 32
LEVEL_ONE_OFFSET = 336
LEVEL_ONE_ENTRIES = 244
DATA_BLOCKS_PER_SECTION = 256
PRIVATE_KEY_FILE_OFFSET = 0x9AC4B0
PRIVATE_KEY_LENGTH = 0x4A7
SIGNING_PUBLIC_KEY_FILE_OFFSET = 0x9AC958
SIGNING_PUBLIC_KEY_LENGTH = 270


def _ctr_crypt(data: bytes, key: bytes, iv: bytes) -> bytes:
    if len(data) % AES.block_size:
        raise ValueError("CTR input is not AES-block aligned")
    counter = bytearray(iv)
    cipher = AES.new(key, AES.MODE_ECB)
    output = bytearray()
    for offset in range(0, len(data), AES.block_size):
        stream = cipher.encrypt(bytes(counter))
        output.extend(left ^ right for left, right in zip(
            data[offset:offset + AES.block_size], stream))
        for index in range(len(counter)):
            counter[index] = (counter[index] + 1) & 0xFF
            if counter[index]:
                break
    return bytes(output)


def load_executable_keys(executable: Path) -> tuple[RSA.RsaKey, RSA.RsaKey]:
    image = executable.read_bytes()
    private_end = PRIVATE_KEY_FILE_OFFSET + PRIVATE_KEY_LENGTH
    public_end = SIGNING_PUBLIC_KEY_FILE_OFFSET + SIGNING_PUBLIC_KEY_LENGTH
    if len(image) < max(private_end, public_end):
        raise ValueError("out.exe is too small for the verified OLFinal key offsets")
    unwrap_private = RSA.import_key(
        image[PRIVATE_KEY_FILE_OFFSET:private_end])
    signing_public = RSA.import_key(
        image[SIGNING_PUBLIC_KEY_FILE_OFFSET:public_end])
    if unwrap_private.size_in_bytes() != SIGNATURE_SIZE or \
            signing_public.size_in_bytes() != SIGNATURE_SIZE:
        raise ValueError("out.exe does not contain the expected RSA-2048 keys")
    return unwrap_private, signing_public


def _unwrap_key(container: bytes, unwrap_private: RSA.RsaKey) -> bytes:
    if len(container) < OUTER_HEADER_SIZE:
        raise ValueError("fastfile is shorter than its outer header")
    wrapped = container[0x15:OUTER_HEADER_SIZE]
    sentinel = secrets.token_bytes(41)
    key_material = PKCS1_v1_5.new(unwrap_private).decrypt(wrapped, sentinel)
    if len(key_material) != 40:
        raise ValueError("fastfile RSA key unwrap failed")
    return key_material


def decrypt_block_zero(container: bytes, unwrap_private: RSA.RsaKey) -> bytes:
    if container[:8] != OUTER_MAGIC:
        raise ValueError("fastfile outer magic is not IWff0100")
    if int.from_bytes(container[8:12], "little") != VERSION:
        raise ValueError("fastfile version is not OLFinal version 461")
    encrypted = container[OUTER_HEADER_SIZE:OUTER_HEADER_SIZE + BLOCK_SIZE]
    if len(encrypted) != BLOCK_SIZE:
        raise ValueError("fastfile has no complete block zero")
    key_material = _unwrap_key(container, unwrap_private)
    return _ctr_crypt(encrypted, key_material[:24], key_material[24:])


def template_signature(container: bytes, unwrap_private: RSA.RsaKey,
                       signing_public: RSA.RsaKey) -> bytes:
    block_zero = decrypt_block_zero(container, unwrap_private)
    if block_zero[:8] != INNER_MAGIC:
        raise ValueError("template inner magic is not IWffs100")
    signed_region = block_zero[
        SIGNED_REGION_OFFSET:SIGNED_REGION_OFFSET + SIGNED_REGION_SIZE]
    digest = hashlib.sha256(signed_region).digest()
    if block_zero[12:44] != digest:
        raise ValueError("template block-zero SHA-256 does not match")
    signature = block_zero[
        SIGNATURE_OFFSET:SIGNATURE_OFFSET + SIGNATURE_SIZE]
    try:
        pkcs1_15.new(signing_public).verify(SHA256.new(signed_region), signature)
    except (ValueError, TypeError) as error:
        raise ValueError("template RSA signature is not valid") from error
    return signature


def _padded_blocks(data: bytes) -> list[bytes]:
    if not data:
        data = b"\0"
    blocks = []
    for offset in range(0, len(data), BLOCK_SIZE):
        block = data[offset:offset + BLOCK_SIZE]
        blocks.append(block.ljust(BLOCK_SIZE, b"\0"))
    return blocks


def pack_zone(zone: bytes, zone_name: str, unwrap_private: RSA.RsaKey,
              borrowed_signature: bytes, *, key_material: bytes | None = None,
              compression_level: int = 1) -> bytes:
    encoded_name = zone_name.encode("ascii")
    if not encoded_name or len(encoded_name) >= ZONE_NAME_SIZE:
        raise ValueError("zone name must be 1..31 ASCII bytes")
    if len(borrowed_signature) != SIGNATURE_SIZE:
        raise ValueError("borrowed RSA signature must be exactly 256 bytes")
    if key_material is None:
        key_material = secrets.token_bytes(40)
    if len(key_material) != 40:
        raise ValueError("AES-192 key and IV material must be exactly 40 bytes")

    compressed = zlib.compress(zone, compression_level)
    data_blocks = _padded_blocks(compressed)
    sections = (len(data_blocks) + DATA_BLOCKS_PER_SECTION - 1) // \
        DATA_BLOCKS_PER_SECTION
    if sections > LEVEL_ONE_ENTRIES:
        raise ValueError("zone exceeds OLFinal's 512 MiB fastfile ceiling")

    block_zero = bytearray(BLOCK_SIZE)
    block_zero[:8] = INNER_MAGIC
    block_zero[SIGNATURE_OFFSET:SIGNATURE_OFFSET + SIGNATURE_SIZE] = \
        borrowed_signature
    block_zero[ZONE_NAME_OFFSET:ZONE_NAME_OFFSET + len(encoded_name)] = \
        encoded_name

    encrypted_payload = bytearray()
    for section_index in range(sections):
        first = section_index * DATA_BLOCKS_PER_SECTION
        section_blocks = data_blocks[first:first + DATA_BLOCKS_PER_SECTION]
        level_two = bytearray(BLOCK_SIZE)
        for index, block in enumerate(section_blocks):
            level_two[index * 32:(index + 1) * 32] = hashlib.sha256(block).digest()
        level_two_digest = hashlib.sha256(level_two).digest()
        level_one_offset = LEVEL_ONE_OFFSET + section_index * 32
        block_zero[level_one_offset:level_one_offset + 32] = level_two_digest
        encrypted_payload.extend(_ctr_crypt(
            bytes(level_two), key_material[:24], level_two_digest[:16]))
        for index, block in enumerate(section_blocks):
            digest = level_two[index * 32:(index + 1) * 32]
            encrypted_payload.extend(_ctr_crypt(
                block, key_material[:24], digest[:16]))

    signed_region = block_zero[
        SIGNED_REGION_OFFSET:SIGNED_REGION_OFFSET + SIGNED_REGION_SIZE]
    block_zero[12:44] = hashlib.sha256(signed_region).digest()
    encrypted_zero = _ctr_crypt(
        bytes(block_zero), key_material[:24], key_material[24:])
    wrapped = PKCS1_v1_5.new(unwrap_private.public_key()).encrypt(key_material)
    header = bytearray(OUTER_HEADER_SIZE)
    header[:8] = OUTER_MAGIC
    header[8:12] = VERSION.to_bytes(4, "little")
    header[12] = 1
    header[0x15:OUTER_HEADER_SIZE] = wrapped
    return bytes(header) + encrypted_zero + bytes(encrypted_payload)


def unpack_zone(container: bytes, unwrap_private: RSA.RsaKey,
                *, expected_name: str | None = None) -> tuple[str, bytes]:
    if (len(container) - OUTER_HEADER_SIZE) % BLOCK_SIZE:
        raise ValueError("fastfile encrypted body is not 0x2000-block aligned")
    block_zero = decrypt_block_zero(container, unwrap_private)
    if block_zero[:8] != INNER_MAGIC:
        raise ValueError("fastfile inner magic is not IWffs100")
    signed_region = block_zero[
        SIGNED_REGION_OFFSET:SIGNED_REGION_OFFSET + SIGNED_REGION_SIZE]
    if block_zero[12:44] != hashlib.sha256(signed_region).digest():
        raise ValueError("fastfile block-zero SHA-256 does not match")
    name_bytes = block_zero[ZONE_NAME_OFFSET:ZONE_NAME_OFFSET + ZONE_NAME_SIZE]
    if name_bytes[-1] != 0:
        raise ValueError("fastfile zone name is not terminated")
    zone_name = name_bytes.split(b"\0", 1)[0].decode("ascii")
    if expected_name is not None and zone_name != expected_name:
        raise ValueError(f"fastfile binds {zone_name!r}, expected {expected_name!r}")

    key_material = _unwrap_key(container, unwrap_private)
    encrypted_blocks = [
        container[offset:offset + BLOCK_SIZE]
        for offset in range(OUTER_HEADER_SIZE + BLOCK_SIZE,
                            len(container), BLOCK_SIZE)
    ]
    compressed = bytearray()
    cursor = 0
    section = 0
    while cursor < len(encrypted_blocks):
        if section >= LEVEL_ONE_ENTRIES:
            raise ValueError("fastfile contains too many hash-table sections")
        level_one_offset = LEVEL_ONE_OFFSET + section * 32
        level_two_digest = block_zero[
            level_one_offset:level_one_offset + 32]
        level_two = _ctr_crypt(
            encrypted_blocks[cursor], key_material[:24], level_two_digest[:16])
        cursor += 1
        if hashlib.sha256(level_two).digest() != level_two_digest:
            raise ValueError(f"level-two hash failed for section {section + 1}")
        for index in range(DATA_BLOCKS_PER_SECTION):
            if cursor >= len(encrypted_blocks):
                break
            digest = level_two[index * 32:(index + 1) * 32]
            block = _ctr_crypt(
                encrypted_blocks[cursor], key_material[:24], digest[:16])
            if hashlib.sha256(block).digest() != digest:
                raise ValueError(
                    f"data hash failed for section {section + 1}, block {index}")
            compressed.extend(block)
            cursor += 1
        section += 1
    return zone_name, zlib.decompress(bytes(compressed))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zone", type=Path, help="inflated .zone body")
    parser.add_argument("output", type=Path, help="destination .ff")
    parser.add_argument("--exe", type=Path, required=True,
                        help="matching OLFinal out.exe")
    parser.add_argument("--template", type=Path, required=True,
                        help="a shipped, validly signed OLFinal .ff")
    parser.add_argument("--name", help="zone binding; defaults to output stem")
    parser.add_argument("--force", action="store_true")
    arguments = parser.parse_args(argv)

    if arguments.output.exists() and not arguments.force:
        parser.error(f"output exists: {arguments.output}; pass --force to replace it")
    zone_name = arguments.name or arguments.output.stem
    unwrap_private, signing_public = load_executable_keys(arguments.exe)
    signature = template_signature(
        arguments.template.read_bytes(), unwrap_private, signing_public)
    zone = arguments.zone.read_bytes()
    container = pack_zone(zone, zone_name, unwrap_private, signature)
    verified_name, verified_zone = unpack_zone(
        container, unwrap_private, expected_name=zone_name)
    if verified_zone != zone:
        raise RuntimeError("internal round-trip verification failed")

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = arguments.output.with_suffix(arguments.output.suffix + ".tmp")
    temporary.write_bytes(container)
    os.replace(temporary, arguments.output)
    print(f"packed {verified_name}: {len(zone)} -> {len(container)} bytes; "
          f"sha256={hashlib.sha256(container).hexdigest()}")
    print("load with OLMOD_ALLOW_UNSIGNED_FASTFILES=1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
