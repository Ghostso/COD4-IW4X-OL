import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE
pe = PE.load()

# Search backward from 0x634090
for test_va in range(0x634090, 0x633F00, -1):
    b = pe.read(test_va, 3)
    if b == b"\x55\x8b\xec" or (pe.read(test_va-1, 1) in [b"\xcc", b"\xc3"] and b[0] in [0x55, 0x56, 0x53, 0x8b]):
        func_start = test_va
        break

print(f"Function containing 0x634090 starts at 0x{func_start:X}")
for l in pe.dis(func_start, 40):
    print(l)
