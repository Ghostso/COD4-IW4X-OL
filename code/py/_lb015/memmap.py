import os, re, struct
D = r"D:\BaiduNetdiskDownload\使命召唤OL\DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT\mem_linear_20261007_134406"
regs=[]
for fn in os.listdir(D):
    m = re.match(r"r_([0-9A-Fa-f]{8})_([0-9A-Fa-f]{8})\.bin$", fn)
    if not m: 
        continue
    base = int(m.group(1),16); size=int(m.group(2),16)
    p = os.path.join(D, fn)
    actual = os.path.getsize(p)
    regs.append((base,size,actual,fn))
regs.sort()
print("regions:", len(regs))
print("total committed bytes:", sum(r[2] for r in regs))
for va in (0x632680, 0xDC7270, 0x849B61C, 0xE34808, 0xE355E8, 0xE35D80, 0xE32C80, 0xE37C00, 0xD55DB0, 0xD5611D, 0xD3D628):
    hit=[r for r in regs if r[0] <= va < r[0]+r[1]]
    print("VA %08X ->" % va, (("base %08X size %08X file %s actual %X" % (hit[0][0],hit[0][1],hit[0][3],hit[0][2])) if hit else "NOT COMMITTED"))
# gaps in low module range
lo,hi=0x400000,0x12659000
cov=[]
cur=lo
for base,size,actual,fn in regs:
    if base>hi or base+size<lo: continue
    b=max(base,lo); e=min(base+size,hi)
    if b>cur: cov.append((cur,b))
    cur=max(cur,e)
if cur<hi: cov.append((cur,hi))
print("gaps count:", len(cov))
for g in cov[:80]:
    print("  gap %08X..%08X  (%X)" % (g[0],g[1],g[1]-g[0]))
