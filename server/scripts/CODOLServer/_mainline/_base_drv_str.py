import re
d=open(r"COD OL\codoMP_client_shipRetailBase.dll","rb").read()
print("=== Base.dll: TerSafe / TCJ / tvsd / 驱动装载 相关全部串 ===")
seen=set()
for m in re.finditer(rb"[\x20-\x7e]{6,}", d):
    s=m.group().decode("latin1")
    low=s.lower()
    if any(k in low for k in ("tersafe","tvsd","tcj","loaddriver","tenloaddriver","real load","ioc tl","ioctl",
                              "\\\\.\\","device\\","\\device","drv","driver")):
        if s in seen: continue
        seen.add(s)
        if any(x in low for x in ("digicert","verisign","microsoft.com","symantec","thawte")): continue
        print("  off 0x%06X %r"%(m.start(), s[:130]))
        if len(seen)>60: break
