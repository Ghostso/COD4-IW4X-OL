import re
for p,keys in [(r"COD OL\ace-ats32.dll", ("http","Http","HTTP","anti","Anti","cheat","Cheat","scan","Scan","detect","Detect","inject","Inject","debug","Debug","VM","hook","Hook","report","Report","url","URL","token","sign","auth")),
               (r"COD OL\ACE-DRV32.dll",  ("dev","Dev","device","Device","\\\\.\\","IOCTL","ioctl","driver","Driver","service","Service","kill","Kill","protect","Protect","hook","Hook"))]:
    d=open(p,"rb").read()
    print("="*68); print(p, len(d))
    seen=set()
    for m in re.finditer(rb"[\x20-\x7e]{6,}", d):
        s=m.group().decode("latin1")
        if any(k in s for k in keys):
            if s in seen: continue
            seen.add(s)
            print("  off 0x%06X %r"%(m.start(), s[:130]))
            if len(seen)>45: break
