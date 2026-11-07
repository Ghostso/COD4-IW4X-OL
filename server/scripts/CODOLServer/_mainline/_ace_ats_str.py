import re
d=open(r"COD OL\ace-ats32.dll","rb").read()
print("=== ace-ats32.dll 全部可疑业务字符串 ===")
seen=set()
for m in re.finditer(rb"[\x20-\x7e]{7,}", d):
    s=m.group().decode("latin1")
    low=s.lower()
    if any(k in low for k in ("bugcheck","tamper","tvm0","vm0","detect","inject","hook","patch","modif",
                              "integrity","hash","verify","scan","cheat","hack","debug","attach","thread",
                              "module","memory","scan","driver","device","ioctl","service","report",
                              "upload","http","token","sign","key","encrypt","decode","protocol")):
        if "digicert" in low or "verisign" in low or "microsoft.com" in low or "symantec" in low or "thawte" in low or "globalsign" in low: continue
        if s in seen: continue
        seen.add(s)
        print("  off 0x%06X %r"%(m.start(), s[:135]))
        if len(seen)>70: break
