import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE
pe = PE.load()

# Let's inspect 0x7F08B0 and 0x7F0970 and other methods in 0x7F0xxx..0x7F2xxx
# Specifically, where does the InstantMessage packet get parsed?
# Let's search for calls to 0xB965D0, 0xB97F20, 0xB8E680, 0xB76AF0 (which we saw in 0x7F1400)
# In 0x7F1400:
#   0x7F1438 call 0xB74220
#   0x7F144A call 0x4F3F60
#   0x7F147B call 0xB76AF0
print("=== Let's inspect who calls 0x7F1400 or invokes vtable + 0x68 ===")
