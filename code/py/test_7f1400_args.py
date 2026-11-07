import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE
pe = PE.load()

# Search for all references to [ebp+8] and [ebp+0xC] in 0x7F1400..0x7F1700
for va in range(0x7F1400, 0x7F1710):
    ins = list(pe.dis(va, 1))
    if ins:
        s = ins[0]
        if "ebp + 8" in s or "ebp + 0xc" in s or "ebp + 0x10" in s or "ebp + 0x14" in s or "ebp + 0x18" in s:
            print(s)
