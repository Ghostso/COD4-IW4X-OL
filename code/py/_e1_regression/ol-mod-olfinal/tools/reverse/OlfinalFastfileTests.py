#!/usr/bin/env python3

from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15

from OlfinalFastfile import (
    BLOCK_SIZE,
    SIGNED_REGION_OFFSET,
    SIGNED_REGION_SIZE,
    decrypt_block_zero,
    pack_zone,
    template_signature,
    unpack_zone,
)


def main() -> None:
    unwrap_private = RSA.generate(2048)
    signing_private = RSA.generate(2048)
    signing_public = signing_private.public_key()
    fixed_key_material = bytes(range(40))

    draft = pack_zone(
        b"template zone", "template", unwrap_private, bytes(256),
        key_material=fixed_key_material)
    draft_zero = decrypt_block_zero(draft, unwrap_private)
    signed_region = draft_zero[
        SIGNED_REGION_OFFSET:SIGNED_REGION_OFFSET + SIGNED_REGION_SIZE]
    valid_signature = pkcs1_15.new(signing_private).sign(
        SHA256.new(signed_region))
    template = pack_zone(
        b"template zone", "template", unwrap_private, valid_signature,
        key_material=fixed_key_material)
    borrowed = template_signature(template, unwrap_private, signing_public)

    zone = bytes(range(256)) * (BLOCK_SIZE // 256 + 3)
    repacked = pack_zone(
        zone, "unit_test", unwrap_private, borrowed,
        key_material=bytes(reversed(range(40))))
    name, round_trip = unpack_zone(
        repacked, unwrap_private, expected_name="unit_test")
    assert name == "unit_test"
    assert round_trip == zone

    corrupted = bytearray(repacked)
    corrupted[-1] ^= 1
    try:
        unpack_zone(bytes(corrupted), unwrap_private)
    except ValueError as error:
        assert "data hash failed" in str(error)
    else:
        raise AssertionError("corrupted data block was accepted")
    print("OLFinal fastfile tests passed")


if __name__ == "__main__":
    main()
