# -*- coding: utf-8 -*-
"""b09: locate gameplay netchan candidates."""
import sys, os, struct, bisect
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import _c046 as C
print("=== dump 0x865380..0x8656C0 (recvfrom/sendto/listen/accept cluster) ===")
print(C.dump(0x865380,0x8656C0))
