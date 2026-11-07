import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE
pe = PE.load()
print("=== Disasm exactly at 0xB95D20 ===")
for l in pe.dis(0xB95D20, 25):
    print(l)
