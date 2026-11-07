# -*- coding: utf-8 -*-
"""定位注册表条目基址 0xE69CE0 / 索引表 0xE4E20C 的读取者 = 真正的分派点。"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

def fs(va):
    for back in range(1, 0x1500):
        x = va - back
        b = pe.read(x, 2)
        if b and b[0] == 0xCC and b[1] == 0xCC: return x + 1
    return None

for disp, label in ((0xE69CE0, "entry base 0xE69CE0"), (0xE4E20C, "index table 0xE4E20C"),
                    (0xE56FFE0, "scan start 0xE56FFE0"), (0xE5713E0, "scan end 0xE5713E0")):
    print("=== %s ===" % label)
    for pre, kind in ((b"\x8b\x0d","mov ecx"),(b"\x8b\x15","mov edx"),(b"\xb8","mov eax"),
                      (b"\x8b\x1d","mov ebx"),(b"\x8b\x35","mov esi"),(b"\x8b\x3d","mov edi"),
                      (b"\x68","push"),(b"\x05","add eax")):
        for o in pe.find_bytes(pre + struct.pack("<I", disp)):
            va = pe.off_to_va(o)
            if va and pe.is_exec(va):
                f = fs(va)
                print("   %08X %-8s (func ~%s)" % (va, kind, hex(f) if f else "?"))
    print()
