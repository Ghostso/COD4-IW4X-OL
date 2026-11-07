"""Decode the return-code constants used by the DW state machine."""
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE = 0x400000
IMAGE = "CODOLServer/_mainline/_dyn100_run_20260925_182324/live/image_best.bin"

blob = open(IMAGE, "rb").read()

for va in (0x7F2994, 0x7F2850, 0x7F25DC, 0x7F3878):
    words = blob[va - BASE: va - BASE + 0x40]
    vals = [
        int.from_bytes(words[i:i + 4], "little")
        for i in range(0, 0x40, 4)
    ]
    print("jump table 0x%08X:" % va)
    for i, val in enumerate(vals):
        print("    idx %2d -> 0x%08X" % (i, val))

print()
print("globals referenced:")
for name, va, size in (
    ("dw_state", 0x84ABA50, 4),
    ("dw_substate", 0x84ABA60, 4),
    ("dw_code", 0x84ABA5C, 4),
    ("dns_ok", 0x84ABA78, 4),
    ("lobby_phase", 0x84ABA7C, 4),
):
    raw = blob[va - BASE: va - BASE + size]
    print("  %-12s 0x%08X = %s" % (name, va, raw.hex()))
