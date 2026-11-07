import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE
pe = PE.load()

for name, va in [("0x5C2D91", 0x5C2D91), ("0x63A840", 0x63A840)]:
    print(f"=== Disasm around {name} ===")
    for l in pe.dis(va - 10, 15):
        print(" ", l)
