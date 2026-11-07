# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8")
s=open(r"_extracted\scripts\demo_parse.py",encoding="utf-8",errors="replace").read().split("\n")
print("\n".join("%4d %s"%(i+1,s[i]) for i in range(250,345)))
