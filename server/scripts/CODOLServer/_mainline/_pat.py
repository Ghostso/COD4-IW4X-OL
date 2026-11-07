"""Wildcard byte-pattern scanner over the decrypted runtime image.

'?' in a pattern matches one nibble.  Spaces are ignored.

Usage:
  python -X utf8 CODOLServer/_mainline/_pat.py "c7 4? 14" 
  python -X utf8 CODOLServer/_mainline/_pat.py "c7 05 60 ba 4a 08"
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
IMAGE = os.path.join(HERE, "_dyn100_run_20260925_182324", "live", "image_best.bin")
BASE = 0x400000


def compile_pat(spec):
    spec = spec.replace(" ", "")
    if len(spec) % 2:
        raise SystemExit("bad pattern length: " + spec)
    out = []
    for i in range(0, len(spec), 2):
        hi, lo = spec[i], spec[i + 1]
        hb = None if hi == "?" else int(hi, 16)
        lb = None if lo == "?" else int(lo, 16)
        out.append((hb, lb))
    return out


def match_at(data, off, pat):
    for i, (hb, lb) in enumerate(pat):
        b = data[off + i]
        if hb is not None and (b >> 4) != hb:
            return False
        if lb is not None and (b & 0xF) != lb:
            return False
    return True


def main(argv):
    with open(IMAGE, "rb") as f:
        data = f.read()
    lo, hi = BASE, BASE + len(data)
    if argv and argv[0] == "--range":
        a, b = argv[1].split(":")
        lo, hi = int(a, 16), int(b, 16)
        argv = argv[2:]
    for spec in argv:
        pat = compile_pat(spec)
        n = len(pat)
        print("=== pattern %s (range %08X..%08X) ===" % (spec, lo, hi))
        hits = 0
        for off in range(max(0, lo - BASE), min(len(data) - n, hi - BASE)):
            if match_at(data, off, pat):
                ctx = data[off:off + 16]
                print("  %08X  %s" % (BASE + off,
                                      " ".join("%02X" % b for b in ctx)))
                hits += 1
        print("  total: %d" % hits)
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
