import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE
pe = PE.load()

# In Demonware, service 11 is Channel / Room Service (bdChannelService)
# Let's search for strings like "ChannelService", "gameStart", "room", "setRoomData"
for s in ["gameStart", "ChannelService", "setRoomData", "RoomData"]:
    pos = pe.find_cstr(s)
    print(f"find_cstr({s}): {len(pos)} hits")
    for off, va in pos:
        print(f"  VA 0x{va:X}")
        refs = pe.find_dword(va)
        for roff, rva in refs:
            print(f"    ref at 0x{rva:X}")
