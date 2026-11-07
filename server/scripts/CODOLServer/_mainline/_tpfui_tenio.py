import re
files=[r"COD OL\IIPS\Tenio\TenTPF.dll", r"COD OL\IIPS\Tenio\June.dll", r"COD OL\IIPS\Tenio\ScriptManager.dll"]
import glob,os
for f in glob.glob(r"COD OL\IIPS\Tenio\*"):
    if os.path.isfile(f): files.append(f)
seen=set()
for f in files:
    if f in seen or not os.path.isfile(f): continue
    seen.add(f)
    d=open(f,"rb").read()
    hits=[]
    for m in re.finditer(rb"[\x20-\x7e]{3,}", d):
        s=m.group().decode("latin1")
        if any(k in s for k in ("TPFUI","IIPSRes","Res\\\\","\\\\%s","Localization","%s\\\\%s","back\\\\")):
            hits.append((m.start(),s))
    if hits:
        print("="*60); print(f, os.path.getsize(f))
        for o,s in hits[:30]:
            print("   off 0x%06X %r"%(o,s[:120]))
