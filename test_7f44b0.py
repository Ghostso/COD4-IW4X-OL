import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE
pe = PE.load()
print("=== Disasm 0x7F44B0 ===")
for l in pe.dis(0x7F44B0, 35):
    print(l)
