# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== who calls 0x6750A0's inner IAT [0xCA8128]? (count only) ===")
print("   (already known: 657 sites)")
print()
print("=== 0x5C05F0 head: state 3 path uses netchan [ebx+0x14..] and posts via 0x675260 ===")
print()
print("=== inspect 0x6751F0's arg 'type': called with [ebp+8] as type; sender must be 2 ===")
print()
print("=== find the actual OS transmit: scan for call dword ptr [reg+8] near packet buffers ===")
print("=== try: find functions that reference the netchan global 0x331C0C8 and call [0xCA8128] ===")
G = 0x0331C0C8
import struct
found = []
for pre, kind in ((b"\x8b\x0d", "mov ecx,[g]"), (b"\xa1", "mov eax,[g]")):
    for o in pe.find_bytes(pre + struct.pack("<I", G)):
        va = pe.off_to_va(o)
        if va and pe.is_exec(va):
            found.append((va, kind))
print("   %d refs" % len(found))
# 打印每个 ref 后 40 字节里是否出现 ff 15 28 81 ca 00
IAT = b"\xff\x15\x28\x81\xca\x00"
for va, kind in sorted(found):
    seg = pe.read(va, 200)
    if seg and IAT in seg:
        print("   %08X %s  -> contains call [0xCA8128]" % (va, kind))
