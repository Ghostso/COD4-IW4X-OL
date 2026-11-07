# -*- coding: utf-8 -*-
import sys,re
sys.stdout.reconfigure(encoding="utf-8")
s=open(r"_extracted\scripts\demo_parse.py",encoding="utf-8",errors="replace").read()
print("LINES",s.count("\n"))
# find tables mentioning idx/width
for m in re.finditer(r"(?m)^.*(WIDTHS|SIZES|FIELD|field_|WIDTH|codec|CODE|idx|INDEX).*$", s):
    print("  >>",m.group()[:160])
