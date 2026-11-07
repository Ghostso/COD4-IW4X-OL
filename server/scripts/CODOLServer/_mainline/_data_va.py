"""Dump raw bytes / dword pointers from the decrypted runtime image by VA.

Usage:
  python -X utf8 CODOLServer/_mainline/_data_va.py --hex 0xB99A28:0xB99A48
  python -X utf8 CODOLServer/_mainline/_data_va.py --ptr 0xD5A1E0:0xD5A240
  python -X utf8 CODOLServer/_mainline/_data_va.py --str 0xD5A228
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
IMAGE = os.path.join(HERE, "_dyn100_run_20260925_182324", "live", "image_best.bin")
BASE = 0x400000


def parse(spec):
    if ":" in spec:
        a, b = spec.split(":", 1)
        return int(a, 16), int(b, 16)
    v = int(spec, 16)
    return v, v + 0x40


def main(argv):
    with open(IMAGE, "rb") as f:
        data = f.read()
    mode = argv[0]
    for spec in argv[1:]:
        start, end = parse(spec)
        blob = data[start - BASE:end - BASE]
        if mode == "--hex":
            for off in range(0, len(blob), 16):
                row = blob[off:off + 16]
                print("%08X  %-47s  %s" % (
                    start + off, " ".join("%02X" % b for b in row),
                    "".join(chr(b) if 32 <= b < 127 else "." for b in row)))
        elif mode == "--ptr":
            for off in range(0, len(blob) - 3, 4):
                v = struct.unpack_from("<I", blob, off)[0]
                print("%08X  %08X" % (start + off, v))
        elif mode == "--str":
            raw = blob.split(b"\x00")[0]
            print("%08X  %r" % (start, raw))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
