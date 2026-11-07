import re
d=open(r"COD OL\PolicyProbe.dll","rb").read()
print("size",len(d))
for m in re.finditer(rb"[\x20-\x7e]{6,}", d):
    s=m.group().decode("latin1")
    if any(k in s for k in ("AntiCheatExpert","SGuard","ace-ats","Policy","policy","stub","Stub","LocalRM","ResourceManager")):
        print("  off 0x%06X %r"%(m.start(), s[:130]))
