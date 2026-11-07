import re
p="_precond.py"
s=open(p,encoding="utf-8").read()
s=s.replace('("flag3D",0x849BA3D)','("flag3D",0x849BA3D),("gate61F",0x849B61F),("tickA",0x849BA30),("tickB",0x849BA34)')
s=s.replace('for nm,va in [','for nm,va in [')
open(p,"w",encoding="utf-8").write(s)
print("patched")
