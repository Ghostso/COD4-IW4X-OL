"""Experiment: isolate which header field actually causes ERROR_BAD_EXE_FORMAT.

Builds 4 byte-level variants of LocalRM.dll (header-only edits, same length)
and lets a07_loadtest.ps1 test each one with the real loader.

  V0  as-is LocalRM.dll
  V1  V0 + SizeOfHeaders fixed to 0x1000
  V2  V1 + SizeOfImage fixed to 0x55000
  V3  V2 + SizeOfCode / SizeOfInitializedData / BaseOfData restored
  V4  V3 + AddressOfEntryPoint restored to RVA 0x1C80
"""
import os
import shutil
import struct

SRC = "LocalRM.dll"
OUTDIR = os.path.join("restore005", "probe")

OPTHDR_OFF = 0x100 + 4 + 20          # start of IMAGE_OPTIONAL_HEADER


def u32(buf, off):
    return struct.unpack_from("<I", buf, off)[0]


def w32(buf, off, v):
    struct.pack_into("<I", buf, off, v)


def set_sizeofheaders(buf, v=0x1000):
    # IMAGE_OPTIONAL_HEADER32.SizeOfHeaders = offset 60
    w32(buf, OPTHDR_OFF + 60, v)


def set_sizeofimage(buf, v=0x55000):
    # SizeOfImage = offset 56
    w32(buf, OPTHDR_OFF + 56, v)


def set_addressofentrypoint(buf, v=0x1C80):
    # AddressOfEntryPoint = offset 16
    w32(buf, OPTHDR_OFF + 16, v)


def set_sizeofcode(buf, v=0x32000):
    w32(buf, OPTHDR_OFF + 4, v)


def set_sizeofinitdata(buf, v=0x20000):
    w32(buf, OPTHDR_OFF + 8, v)


def set_baseofdata(buf, v=0x33000):
    # BaseOfData = offset 24
    w32(buf, OPTHDR_OFF + 24, v)


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    with open(SRC, "rb") as f:
        base = bytearray(f.read())

    variants = {}
    b = bytearray(base)
    variants["v0_asis.dll"] = bytes(b)

    b = bytearray(base)
    set_sizeofheaders(b)
    variants["v1_sizeofheaders.dll"] = bytes(b)

    b = bytearray(base)
    set_sizeofheaders(b)
    set_sizeofimage(b)
    variants["v2_image_size.dll"] = bytes(b)

    b = bytearray(base)
    set_sizeofheaders(b)
    set_sizeofimage(b)
    set_sizeofcode(b)
    set_sizeofinitdata(b)
    set_baseofdata(b)
    variants["v3_optrestore.dll"] = bytes(b)

    b = bytearray(base)
    set_sizeofheaders(b)
    set_sizeofimage(b)
    set_sizeofcode(b)
    set_sizeofinitdata(b)
    set_baseofdata(b)
    set_addressofentrypoint(b)
    variants["v4_ep_restore.dll"] = bytes(b)

    for name, blob in variants.items():
        p = os.path.join(OUTDIR, name)
        with open(p, "wb") as f:
            f.write(blob)
        print("wrote %s (%d bytes)" % (p, len(blob)))


if __name__ == "__main__":
    main()
