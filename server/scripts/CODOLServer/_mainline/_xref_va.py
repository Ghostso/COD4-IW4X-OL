"""Find direct call/jmp sites (rel32) and absolute data references to a VA.

Usage:
  python -X utf8 CODOLServer/_mainline/_xref_va.py 0xB9A470 0xB999C0
  python -X utf8 CODOLServer/_mainline/_xref_va.py --data 0xB99A28

Read-only analysis over the decrypted runtime image (base 0x400000).
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
IMAGE = os.path.join(HERE, "_dyn100_run_20260925_182324", "live", "image_best.bin")
BASE = 0x400000


def main(argv):
    with open(IMAGE, "rb") as f:
        data = f.read()
    want_data = argv and argv[0] == "--data"
    if want_data:
        argv = argv[1:]
    for spec in argv:
        target = int(spec, 16)
        print("=== refs to %08X ===" % target)
        if not want_data:
            found = 0
            for i in range(len(data) - 5):
                op = data[i]
                if op != 0xE8 and op != 0xE9:
                    continue
                rel = struct.unpack_from("<i", data, i + 1)[0]
                tgt = BASE + i + 5 + rel
                if tgt == target:
                    print("  call/jmp @ %08X" % (BASE + i))
                    found += 1
            print("  total call/jmp: %d" % found)
        abs_pat = struct.pack("<I", target)
        i = data.find(abs_pat)
        n = 0
        while i != -1:
            print("  data @ %08X" % (BASE + i))
            n += 1
            i = data.find(abs_pat, i + 1)
        print("  total abs: %d" % n)
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
