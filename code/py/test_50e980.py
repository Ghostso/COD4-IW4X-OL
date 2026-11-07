import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE
pe = PE.load()
print("=== Disasm 0x50E970..0x50EA20 ===")
for l in pe.dis(0x50E970, 35):
    print(l)
