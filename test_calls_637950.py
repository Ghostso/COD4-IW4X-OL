import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE
pe = PE.load()
calls = pe.calls_to(0x637950)
print(f"Calls to 0x637950: {len(calls)}")
for c in calls:
    print(f"  Call at 0x{c:X}")
