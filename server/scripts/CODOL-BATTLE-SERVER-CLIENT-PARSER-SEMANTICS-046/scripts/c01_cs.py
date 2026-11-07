# -*- coding: utf-8 -*-
import sys,os
sys.stdout.reconfigure(encoding="utf-8")
s=open(r"_extracted\reference\CodolLocalBattleServer.cs",encoding="utf-8",errors="replace").read()
print("LEN",len(s))
print(s[:6000])
