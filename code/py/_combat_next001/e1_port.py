# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

TARGET = 0x2071
print("=== immediate 0x2071 (28960) occurrences ===")
tot = 0
for pre, kind in ((b"\x68", "push"), (b"\xb8", "mov eax"), (b"\xb9", "mov ecx"),
                  (b"\xba", "mov edx"), (b"\xbb", "mov ebx"), (b"\xbe", "mov esi"),
                  (b"\xbf", "mov edi"), (b"\x66\xb8", "mov ax")):
    pat = pre + struct.pack("<I", TARGET)
    for o in pe.find_bytes(pat):
        va = pe.off_to_va(o)
        if va and pe.is_exec(va):
            tot += 1
            print("   %-8s %08X" % (kind, va))
print("total =", tot)
