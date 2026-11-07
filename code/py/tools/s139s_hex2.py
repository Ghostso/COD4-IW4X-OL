# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
d = open(r"E:\codol_re\client_image_20261027.bin", "rb").read()
VA = 0x400000
for lo, hi in ((0xB7B740, 0xB7B7A0), (0xB7B950, 0xB7B9B0)):
    print(f"--- 0x{lo:08X} ---")
    for r in range(lo - VA, hi - VA, 16):
        print(f"  0x{r+VA:08X}  " + " ".join(f"{x:02x}" for x in d[r:r+16]))
