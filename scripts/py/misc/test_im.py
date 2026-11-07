import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE
pe = PE.load()

# Search for references to strings like "InstantMessage" or service 6
for s in ["InstantMessage", "bdInstantMessage", "lobby"]:
    pos = pe.find_cstr(s)
    print(f"find_cstr({s}): {len(pos)} hits")
    for off, va in pos:
        print(f"  VA 0x{va:X}")
        # search for refs to this VA
        refs = pe.find_dword(va)
        for roff, rva in refs:
            print(f"    ref at 0x{rva:X}")
