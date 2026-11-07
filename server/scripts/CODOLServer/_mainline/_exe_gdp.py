import pefile, re, struct
p=r"COD OL\codoMP_client_shipRetail.exe"
d=open(p,"rb").read()
print("=== exe 内 GDPLoader / InitGdp 相关串 ===")
for k in (b"GDPLoader", b"InitGdp", b"GDPLoader.dll", b"GDPImpl", b"GameDataPlatformServer"):
    i=0;h=[]
    while True:
        j=d.find(k,i)
        if j<0: break
        h.append(j); i=j+1
        if len(h)>8: break
    print("  %-24r -> %s"%(k,[hex(x) for x in h]))
print()
print("=== 含 GDP 的 exe 串（前 40）===")
seen=set()
for m in re.finditer(rb"[\x20-\x7e]{5,}", d):
    s=m.group().decode("latin1")
    if "GDP" in s and s not in seen:
        seen.add(s); print("  VA 0x%08X %r"%(0x714000+m.start(), s[:110]))
        if len(seen)>40: break
