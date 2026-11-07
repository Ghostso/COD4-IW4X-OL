import re
for f in [r"COD OL\IIPS\iips_policymsg.dll", r"COD OL\IIPS\iips.dll"]:
    d=open(f,"rb").read()
    print("="*70)
    print(f, len(d))
    for m in re.finditer(rb"[\x20-\x7e]{5,}", d):
        s=m.group().decode("latin1")
        if any(k in s for k in ("udp://","http://","\\\\.\\pipe","Pipe","pipe","iips","IIPS","ctrl","policy","Policy","%s","%d","port","Port","addr","Addr","version","Version","magic","Magic")):
            print("  +0x%06X %r" % (m.start(), s[:120]))
