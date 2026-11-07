import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE
pe = PE.load()
refs = pe.find_dword(0x6379E0)
print(f"Dword refs to 0x6379E0: {len(refs)}")
for off, va in refs:
    print(f"  at VA 0x{va:X}")
