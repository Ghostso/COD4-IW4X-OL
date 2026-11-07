import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE
pe = PE.load()

for name, va in [("0xB74220", 0xB74220), ("0x4F3F60", 0x4F3F60), ("0xB76AF0", 0xB76AF0)]:
    print(f"=== Disasm {name} ===")
    for l in pe.dis(va, 15):
        print(" ", l)
