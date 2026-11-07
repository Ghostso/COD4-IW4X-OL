# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import _c046 as C
txt = C.dump(0x85D5A0, 0x85DA90, "func_A containing 0x85D96E")
C.w(os.path.join(C.EV,"a02_func_85D5A0.txt"), txt)
print(txt)
