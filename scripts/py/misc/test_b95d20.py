import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE
pe = PE.load()
print("=== Disasm 0xB95D10..0xB95D60 ===")
for l in pe.dis(0xB95D10, 30):
    print(l)
