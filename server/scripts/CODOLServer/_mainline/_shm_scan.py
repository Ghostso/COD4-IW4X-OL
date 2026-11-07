"""Scan the TCLS / TenProxy shared-memory images: strings + early hexdump.

Usage:
  python -X utf8 CODOLServer/_mainline/_shm_scan.py
  python -X utf8 CODOLServer/_mainline/_shm_scan.py --hex 0x000:0x100
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SUB = os.path.abspath(os.path.join(HERE, "..", "_subagents"))
IMAGES = ["_tenproxy_shm.bin", "_tenproxy_shm_fixed.bin",
          "_tcls_shm_full_fixed.bin", "_tcls_shm_sample.bin"]


def dump(data, start, end):
    for off in range(start, min(end, len(data)), 16):
        row = data[off:off + 16]
        print("%06X  %-47s  %s" % (
            off, " ".join("%02X" % b for b in row),
            "".join(chr(b) if 32 <= b < 127 else "." for b in row)))


def main(argv):
    if argv and argv[0] == "--hex":
        a, b = argv[1].split(":")
        data = open(os.path.join(SUB, IMAGES[0]), "rb").read()
        dump(data, int(a, 16), int(b, 16))
        return 0

    for name in IMAGES:
        path = os.path.join(SUB, name)
        if not os.path.isfile(path):
            print("%-26s MISSING" % name)
            continue
        data = open(path, "rb").read()
        print("%-26s size=%d" % (name, len(data)))
        for m in list(re.finditer(rb"[ -~]{5,}", data))[:20]:
            print("    %06X  %r" % (m.start(), m.group()[:90]))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
