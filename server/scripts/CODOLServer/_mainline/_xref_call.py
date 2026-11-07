"""List direct E8 call sites targeting given VAs in the decrypted image."""
import struct
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
IMAGE = os.path.join(HERE, "_dyn100_run_20260925_182324", "live", "image_best.bin")
BASE = 0x400000


def callers(data, target):
    out = []
    for i in range(len(data) - 5):
        if data[i] == 0xE8:
            rel = struct.unpack_from("<i", data, i + 1)[0]
            if (BASE + i + 5 + rel) & 0xFFFFFFFF == target:
                out.append(BASE + i)
    return out


def main(argv):
    data = open(IMAGE, "rb").read()
    for spec in argv:
        t = int(spec, 16)
        cs = callers(data, t)
        print("calls to %08X: %d" % (t, len(cs)))
        for c in cs:
            print("   %08X" % c)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
