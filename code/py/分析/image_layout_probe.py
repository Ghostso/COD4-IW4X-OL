import sys

sys.stdout.reconfigure(encoding="utf-8")

PATH = "CODOLServer/_fullimage/run1/fullimage/image_best.bin"

blob = open(PATH, "rb").read()

SIGNATURES = [
    ("4FCEE0-history", bytes.fromhex("55 8b ec 81 ec 34 04 00 00")),
    ("4FD287-history", bytes.fromhex("e8 c4 b3 30 00 6a 18 e8")),
    ("808650-history", bytes.fromhex("55 8b ec 83 ec 08 53 56")),
    ("0040 MZ", b"MZ"),
    ("PE00", b"PE\x00\x00"),
    ("auth_task", b"auth_task"),
    ("DW-Server-Ticket", b"DW-Server-Ticket"),
]

for name, needle in SIGNATURES:
    hits = []
    start = 0
    while True:
        idx = blob.find(needle, start)
        if idx < 0:
            break
        hits.append(idx)
        start = idx + 1
        if len(hits) >= 30:
            break
    print("%-20s hits=%d" % (name, len(hits)))
    for hit in hits[:30]:
        print("    file 0x%08X  ifbase400000 VA 0x%08X" % (hit, 0x400000 + hit))
