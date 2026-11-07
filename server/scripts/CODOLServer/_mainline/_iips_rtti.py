import re
for f in [r"COD OL\IIPS\iips.dll", r"COD OL\IIPS\iips_policymsg.dll", r"COD OL\IIPS\IIPSHost.dll"]:
    d=open(f,"rb").read()
    print("="*70); print(f)
    seen=set()
    for m in re.finditer(rb"\.\?AV([A-Za-z0-9_@?$]{2,60})@@", d):
        n=m.group(1).decode("latin1")
        if n not in seen:
            seen.add(n); print("   RTTI", n)
