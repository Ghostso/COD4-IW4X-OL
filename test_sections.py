import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE
pe = PE.load()
for s in pe.sections:
    print(s.name, hex(s.vaddr), hex(s.vsize))
