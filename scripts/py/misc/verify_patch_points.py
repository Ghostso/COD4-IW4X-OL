import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE
import capstone

pe = PE.load()
cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

patches = [
    ("Gate 1 (0x632694)", 0x632694, 6),
    ("Gate 3 (0x6326B0)", 0x6326B0, 6),
    ("Gate 4 (0x6326BF)", 0x6326BF, 6),
    ("Gate 5 (0x6326CE)", 0x6326CE, 6),
    ("Slot match check 1 (0x632705)", 0x632705, 2),
    ("Slot match jump (0x632710)", 0x632710, 2),
    ("Battle bridge skip (0x632822)", 0x632822, 2),
]

for name, va, length in patches:
    raw = pe.read(va - 4, length + 8)
    print(f"=== {name} at 0x{va:X} ===")
    for ins in cs.disasm(raw, va - 4):
        marker = " <--- PATCH TARGET" if ins.address == va else ""
        print(f"  0x{ins.address:08X}  {ins.bytes.hex():12} {ins.mnemonic:6} {ins.op_str}{marker}")
