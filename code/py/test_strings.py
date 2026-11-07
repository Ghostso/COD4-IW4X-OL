import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE
pe = PE.load()

for va in range(0x7F0A00, 0x7F2200):
    b = pe.read(va, 5)
    if b[0] == 0x68:
        target = int.from_bytes(b[1:5], "little")
        if 0x400000 <= target <= 0xE00000:
            raw = pe.read(target, 32)
            s = raw.split(b"\x00")[0]
            if len(s) >= 3 and all(32 <= c < 127 for c in s):
                print(f"At 0x{va:X}: push '{s.decode()}' (0x{target:X})")
