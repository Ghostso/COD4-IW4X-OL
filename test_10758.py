import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE
pe = PE.load()

for va in [0x62C1F3, 0x62F672, 0x633F61]:
    print(f"=== Disasm around 0x{va:X} ===")
    for l in pe.dis(va - 10, 12):
        print(" ", l)
