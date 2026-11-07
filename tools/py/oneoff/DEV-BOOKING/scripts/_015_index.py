# -*- coding: utf-8 -*-
"""015: build a global instruction-start index by resync linear sweep.

Writes a pickle next to this script: _015_idx.pkl  (set of VAs).
Usage: python _015_index.py [lo] [hi]
"""
import os
import pickle
import sys

sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\DEV-BOOKING\scripts")
from _015_lib import BASE, DATA, END, MD  # noqa

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_015_idx.pkl")

lo = int(sys.argv[1], 16) if len(sys.argv) > 1 else BASE
hi = int(sys.argv[2], 16) if len(sys.argv) > 2 else END

starts = set()
pos = lo
n = 0
bad = 0
while pos < hi:
    code = DATA[pos - BASE: min(hi - BASE, pos - BASE + 16)]
    ins = next(MD.disasm(code, pos), None)
    if ins is None or ins.size == 0 or pos + ins.size > hi:
        bad += 1
        pos += 1
        continue
    starts.add(pos)
    n += 1
    pos += ins.size

print("instructions %d, resync events %d, range 0x%X..0x%X" % (n, bad, lo, hi))
pickle.dump(starts, open(OUT, "wb"))
print("wrote", OUT)
