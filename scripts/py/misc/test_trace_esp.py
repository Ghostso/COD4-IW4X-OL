import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE
pe = PE.load()

# Trace instructions from 0x7F1460 to 0x7F14F0
for l in pe.dis(0x7F1460, 35):
    print(l)
