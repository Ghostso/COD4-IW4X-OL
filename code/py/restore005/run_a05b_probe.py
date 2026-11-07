"""Isolate the fatal field with a TRUE 32-bit loader.

Hypothesis: the loader maps the file as a ROM image and validates that the
whole file (including the signed-image certificate / overlay that lives in the
SECURITY directory at RVA 0x53000, i.e. past EOF->SizeOfImage) fits inside
SizeOfImage.  Any SizeOfImage < 0x53000 therefore yields ERROR_BAD_EXE_FORMAT.

Variants built here (pure header bytes, same file length, no section edits):

  w0_asis        : LocalRM.dll unmodified                       (expect FAIL 193)
  w1_soi_legacy  : SizeOfImage -> 0x55000                       (expect ???)
  w2_soi_legacy_soh : + SizeOfHeaders -> 0x1000                 (expect PASS)
"""
import os
import struct

SRC = "LocalRM.dll"
OUTDIR = os.path.join("restore005", "probe")
OPTHDR_OFF = 0x118


def w32(buf, off, v):
    struct.pack_into("<I", buf, off, v)


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    with open(SRC, "rb") as f:
        base = bytearray(f.read())

    variants = {}
    variants["w0_asis.dll"] = bytes(bytearray(base))

    b = bytearray(base)
    w32(b, OPTHDR_OFF + 56, 0x55000)          # SizeOfImage
    variants["w1_soi_legacy.dll"] = bytes(b)

    b = bytearray(base)
    w32(b, OPTHDR_OFF + 56, 0x55000)          # SizeOfImage
    w32(b, OPTHDR_OFF + 60, 0x1000)           # SizeOfHeaders
    variants["w2_soi_legacy_soh.dll"] = bytes(b)

    for name, blob in variants.items():
        p = os.path.join(OUTDIR, name)
        with open(p, "wb") as f:
            f.write(blob)
        print("wrote %s (%d bytes)" % (p, len(blob)))


if __name__ == "__main__":
    main()
