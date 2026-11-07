import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE
pe = PE.load()
print("=== Disasm around 0x62DE9C ===")
for l in pe.dis(0x62DE80, 40):
    print(l)
