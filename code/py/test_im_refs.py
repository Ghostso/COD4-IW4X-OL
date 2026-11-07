import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE
pe = PE.load()

for va in [0xDD503C, 0xDD5056]:
    raw = pe.read(va, 32)
    s = raw.split(b"\x00")[0]
    print(f"VA 0x{va:X}: {s}")
    refs = pe.find_dword(va)
    for roff, rva in refs:
        print(f"  ref at 0x{rva:X}")
