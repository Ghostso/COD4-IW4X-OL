import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE
pe = PE.load()

for va in [0xd5a114, 0xd5a0fc, 0xd5a0e8]:
    raw = pe.read(va, 32)
    s = raw.split(b"\x00")[0]
    print(f"VA 0x{va:X}: {s}")
