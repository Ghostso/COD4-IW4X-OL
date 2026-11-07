import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE
pe = PE.load()

for va in [0x62FDE0, 0x630480]:
    print(f"=== Disasm 0x{va:X} ===")
    for l in pe.dis(va, 20):
        print(" ", l)
