# -*- coding: utf-8 -*-
import sys,json,re
sys.stdout.reconfigure(encoding="utf-8")
d=json.load(open(r"_extracted\reference\playerstate-fields.json",encoding="utf-8"))
print("playerstate-fields.json:",type(d), (list(d.keys())[:20] if isinstance(d,dict) else len(d)))
if isinstance(d,dict):
    for k in list(d)[:5]:
        print("  KEY",k,"->",str(d[k])[:300])
else:
    print(json.dumps(d[:6],ensure_ascii=False,indent=1)[:2000])
