"""EB-003 Agent 03b - dump the resolution string cluster in the EXE.

a03 located "GetResourceManagerII" / "ReleaseResourceManagerII" / "IIPS\\iips.dll"
as NUL-terminated ASCII in the EXE's read-only data. This dumps the whole cluster
so the lookup contract (which names, in which order, next to which other API
names) is visible as raw bytes rather than inferred.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "COD OL")

path = os.path.join(GAME, "codoMP_client_shipRetail.exe")
d = open(path, "rb").read()

START = 0x6B5200
END = 0x6B5460

print("=== EXE .rdata resolution cluster [0x%X, 0x%X) ===" % (START, END))
blk = d[START:END]
# Split on NULs and print only printable runs with their offsets.
run = bytearray()
run_start = START


def flush(start, data):
    if len(data) >= 4:
        try:
            s = data.decode("ascii")
            if all(0x20 <= ord(c) < 0x7F for c in s):
                print("  0x%-8X %r" % (start, s))
        except Exception:
            pass


for i, b in enumerate(blk):
    if b == 0:
        flush(run_start, bytes(run))
        run = bytearray()
    else:
        if len(run) == 0:
            run_start = START + i
        run.append(b)
flush(run_start, bytes(run))

print()
print("=== exact bytes at the three known offsets ===")
for off in (0x6B5294, 0x6B52AC, 0x6B53F5):
    e = d.find(b"\0", off)
    print("  0x%X: %r" % (off, d[off:e].decode("latin1")))

sys.exit(0)
