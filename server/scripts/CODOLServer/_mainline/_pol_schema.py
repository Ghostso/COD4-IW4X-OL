import re
d=open(r"COD OL\IIPS\iips_policymsg.dll","rb").read()
seg=d[0xC400:0xE500]
print("=== iips_policymsg.dll .rdata schema region 0xC400..0xE500 ===")
for m in re.finditer(rb"[\x20-\x7e]{3,}", seg):
    print("+0x%06X %r" % (0xC400+m.start(), m.group().decode("latin1")[:120]))
