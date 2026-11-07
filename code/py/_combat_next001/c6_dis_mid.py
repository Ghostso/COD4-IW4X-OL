# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
lines = pe.dis(0x5C06E0, 130)
out = []
out.append("=== 0x5C06E0 .. (getchallenge format use + following calls) ===")
out.extend(lines)
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "c6_out.txt"), "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out))
