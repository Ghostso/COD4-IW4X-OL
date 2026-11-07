import re, glob, os
pats=[rb"[\x20-\x7e]{0,40}TPFUI[\x20-\x7e]{0,60}", rb"[\x20-\x7e]{0,40}IIPSRes"]
for f in [r"COD OL\IIPS\IIPSHostApp.exe", r"COD OL\IIPS\IIPSHost.dll", r"COD OL\IIPS\iips.dll"]:
    d=open(f,"rb").read()
    print("="*60); print(f)
    for p in pats:
        for m in re.finditer(p, d):
            print("   off 0x%06X %r"%(m.start(), m.group().decode("latin1")))
