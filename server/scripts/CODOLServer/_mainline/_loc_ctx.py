d=open(r"COD OL\localization.txt","rb").read()
txt=d.decode("gbk","replace")
lines=txt.splitlines()
for i,l in enumerate(lines):
    if "DW_LIVE" in l or "SYS_QQID" in l or "WIN_IIPS_INIT" in l:
        print("line %d: %r"%(i+1,l))
        for k in range(1,4):
            if i+k < len(lines): print("        +%d %r"%(k,lines[i+k]))
