import re
b=open(r"COD OL\codoMP_client_shipRetail.exe","rb").read()
print("=== exe 内 211.147.81.116 ===")
i=0
while True:
    j=b.find(b"211.147.81.116",i)
    if j<0: break
    print("  off 0x%06X VA 0x%08X"%(j, 0x714000+j))
    s=max(0,j-200); e=min(len(b),j+260)
    seg=b[s:e]; k=0
    print("    --- 上下文 ---")
    while k<len(seg):
        m=k
        while m<len(seg) and 32<=seg[m]<127: m+=1
        if m-k>=3: print("      VA 0x%08X %r"%(0x714000+s+k, seg[k:m].decode("latin1")[:110])); k=m
        else: k+=1
    i=j+1
print()
print("=== exe 内所有 IP 串 ===")
seen=set()
for m in re.finditer(rb"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", b):
    s=m.group().decode()
    if s in seen: continue
    seen.add(s); print("   VA 0x%08X  %s"%(0x714000+m.start(), s))
