import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE
pe = PE.load()

# Search for all ret instructions in 0x7F1400..0x7F1700
for va in range(0x7F1400, 0x7F1710):
    b = pe.read(va, 3)
    if b[0] == 0xC2: # ret imm16
        imm = int.from_bytes(b[1:3], "little")
        print(f"ret 0x{imm:X} at 0x{va:X}")
    elif b[0] == 0xC3:
        print(f"ret at 0x{va:X}")
