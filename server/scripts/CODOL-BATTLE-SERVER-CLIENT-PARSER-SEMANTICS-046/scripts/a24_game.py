# -*- coding: utf-8 -*-
"""a24: game protocol area near gamestateupdate (0x73214)."""
import sys, os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import _c046 as C
print(C.dump(0x73000,0x73500))
