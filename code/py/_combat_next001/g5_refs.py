# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

def refs(addr, label):
    print("=== refs to %s (0x%08X) ===" % (label, addr))
    n = 0
    for pre, kind in ((b"\x68","push"),(b"\xb8","mov eax"),(b"\xb9","mov ecx"),
                      (b"\xba","mov edx"),(b"\xbb","mov ebx"),(b"\xbe","mov esi"),
                      (b"\xbf","mov edi"),(b"\xbd","mov ebp"),(b"\x8b\x0d","mov ecx,["),
                      (b"\x8b\x15","mov edx,["),(b"\x8b\x1d","mov ebx,["),
                      (b"\x89\x0d","mov [.],ecx"),(b"\x89\x15","mov [.],edx"),
                      (b"\x89\x1d","mov [.],ebx"),(b"\xc7\x05","mov [.],imm")):
        for o in pe.find_bytes(pre + struct.pack("<I", addr)):
            va = pe.off_to_va(o)
            if va and pe.is_exec(va):
                n += 1
                if n <= 25:
                    print("   %-10s %08X" % (kind, va))
    print("   total=%d" % n)

refs(0x470360, "battle-connect func")
refs(0x5C05F0, "battle state machine")
refs(0x331C0C8, "netchan object")
