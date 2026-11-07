import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE
pe = PE.load()

targets = [
    0xB984B0, 0xB984CB, 0xB98529, 0xB989D5, 0xB98A3B,
    0xB9958D, 0xB996BC, 0xB9970A, 0xB9978B, 0xB997E2,
    0xB99D9E, 0xB99DEB, 0xB99F4C, 0xB9A549, 0xB9A5C1,
    0xB9A62C, 0xB9A66D, 0xB9A6EE, 0xB9ABBF, 0xB9C626,
    0xB9C795, 0xB9C886, 0xB9CA15
]

for va in targets:
    # check how many pushes before the call
    insns = list(pe.dis(va - 30, 10))
    for idx, ins in enumerate(insns):
        if f"{va:08x}" in ins.lower() and "call" in ins:
            print(f"=== Call at 0x{va:X} ({ins}) ===")
            for prev in insns[max(0, idx-6) : idx]:
                print("  ", prev)
