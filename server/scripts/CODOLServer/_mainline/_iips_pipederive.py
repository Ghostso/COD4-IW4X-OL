import re
d=open(r"COD OL\IIPS\iips.dll","rb").read()
# around IIPS/%hu/%hu/%hu/%hu  (0x35ED8) - dump the surrounding bytes raw
o=0x35E00
print("=== raw .rdata 0x35E00..0x36000 (strings + fmt) ===")
seg=d[o:o+0x200]
i=0
while i < len(seg):
    j=i
    while j<len(seg) and 32<=seg[j]<127: j+=1
    if j-i>=3:
        print("+0x%06X %r"%(o+i, seg[i:j].decode("latin1")))
        i=j
    else:
        i+=1
print()
# also IIPSClient.ini related and key derivation
for key in [b"IIPS/", b"%hu/%hu/%hu/%hu", b"IIPS Unknown version", b"getkey", b"sharekey", b"ShareKey"]:
    i=d.find(key)
    print("%r @ %s"%(key, hex(i) if i>=0 else "none"))
