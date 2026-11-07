import re
d=open(r"COD OL\IIPS\iips_policymsg.dll","rb").read()
print("size",len(d))
for m in re.finditer(rb"[\x20-\x7e]{4,}", d):
    s=m.group().decode("latin1")
    # skip cert/url noise
    if any(k in s for k in ("http","ocsp","crl","verisign","symantec","thawte","manifest","assembly","Microsoft.VC")):
        continue
    print("+0x%06X %r" % (m.start(), s[:150]))
