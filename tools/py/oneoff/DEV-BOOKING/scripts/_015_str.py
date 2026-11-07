# -*- coding: utf-8 -*-
"""015: search printable strings in image_best.bin, report VA + optional xrefs."""
import re
import struct
import sys

sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\DEV-BOOKING\scripts")
from _015_lib import BASE, DATA, END  # noqa

MIN = 4
pat = re.compile(rb"[\x20-\x7e]{%d,}" % MIN)

needles = [s.lower() for s in sys.argv[1:]] if len(sys.argv) > 1 else None

for m in pat.finditer(DATA):
    s = m.group().decode("ascii")
    if needles and not any(n in s.lower() for n in needles):
        continue
    va = BASE + m.start()
    print("0x%08X  %s" % (va, s))
