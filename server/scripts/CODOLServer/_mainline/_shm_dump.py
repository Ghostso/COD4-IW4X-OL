"""Hexdump a chosen TCLS/TenProxy shm image range.

Usage:
  python -X utf8 CODOLServer/_mainline/_shm_dump.py _tenproxy_shm.bin 0x400:0x4A0
  python -X utf8 CODOLServer/_mainline/_shm_dump.py _tcls_shm_sample.bin 0x2E0:0x3A0
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SUB = os.path.abspath(os.path.join(HERE, "..", "_subagents"))


def main(argv):
    name = argv[0]
    a, b = argv[1].split(":") if len(argv) > 1 else ("0", "0x100")
    path = os.path.join(SUB, name)
    data = open(path, "rb").read()
    start, end = int(a, 16), int(b, 16)
    print("%s  size=%d  range %06X..%06X" % (name, len(data), start, end))
    for off in range(start, min(end, len(data)), 16):
        row = data[off:off + 16]
        print("%06X  %-47s  %s" % (
            off, " ".join("%02X" % x for x in row),
            "".join(chr(x) if 32 <= x < 127 else "." for x in row)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
