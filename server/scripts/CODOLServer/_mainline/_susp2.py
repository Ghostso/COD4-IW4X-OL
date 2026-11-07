import re
for f in [r"COD OL\IIPS\Download.dll", r"COD OL\IIPS\p2papp.dll"]:
    d=open(f,"rb").read()
    print("="*70); print(f)
    for m in re.finditer(rb"[\x20-\x7e]{6,}", d):
        s=m.group().decode("latin1")
        if any(k in s for k in ("ldap","ldap://","p2p","P2P","tracker","Tracker","magnet","bt_","torrent","announce","http://","https://","udp://","v6","ipv6")):
            print("   off 0x%06X %r"%(m.start(), s[:120]))
