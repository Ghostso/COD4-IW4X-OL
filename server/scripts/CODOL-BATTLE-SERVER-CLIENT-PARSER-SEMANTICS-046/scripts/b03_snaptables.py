# -*- coding: utf-8 -*-
import sys,re
sys.stdout.reconfigure(encoding="utf-8")
s=open(r"_extracted\scripts\demo_parse.py",encoding="utf-8",errors="replace").read().split("\n")
for i,l in enumerate(s):
    if re.search(r"SNAP_(U16|F32|SCALAR_W|PRES_RAW|U8|ANG)|^SNAP|def parse_snapshot|def decode", l):
        print("%4d %s"%(i+1,l))
