import hashlib
import sys

sys.stdout.reconfigure(encoding="utf-8")

PATH = (
    sys.argv[1]
    if len(sys.argv) > 1
    else "CODOLServer/_fullimage/run2/fullimage/image_best.bin"
)
BASE = 0x400000

blob = open(PATH, "rb").read()
print("image: %s" % PATH)
print("size : 0x%X (%d)" % (len(blob), len(blob)))
print("nonzero: %d" % sum(1 for b in blob if b))
print("sha256: %s" % hashlib.sha256(blob).hexdigest())
print("assumed base: 0x%08X" % BASE)
print()

PROBES = [
    0x4FCEE0,
    0x4FD287,
    0x808650,
    0x77EE40,
    0x7E98F0,
    0x7F25B0,
    0x7F26C0,
    0x7F28F0,
    0x7F2B90,
    0x7F34E0,
    0x7F3600,
    0x7F306C,
    0xB991A0,
    0xB983F0,
    0xBA9BC0,
    0xB88B80,
    0xBAEAB0,
    0xBAEDF0,
    0xB9A100,
]

for va in PROBES:
    off = va - BASE
    if off < 0 or off + 16 > len(blob):
        print("0x%08X  OUT OF RANGE" % va)
        continue
    data = blob[off : off + 16]
    print("0x%08X : %s" % (va, " ".join("%02x" % b for b in data)))
