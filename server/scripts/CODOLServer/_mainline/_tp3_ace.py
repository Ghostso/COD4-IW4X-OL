import re
d=open(r"COD OL\TP3Helper.exe","rb").read()
for m in re.finditer(rb"[\x20-\x7e]{5,}", d):
    s=m.group().decode("latin1")
    if any(k in s.lower() for k in ("ace","sguard","anticheat","ats","drive","\\\\.\\","driver","\\\\.\\pipe","service")):
        print("  off 0x%06X %r"%(m.start(), s[:130]))
