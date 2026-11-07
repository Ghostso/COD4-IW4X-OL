#!/usr/bin/env python3
"""VA 映射: 从 KEY_CONTEXT 得知 file+0x714000=VA。用该映射搜指向服务名串的指针(u32 VA),
并尝试解析可能的 {name_ptr, id} 结构数组。"""
import struct

PATH = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe"
data = open(PATH, "rb").read()

# 校准: profiles file 0x6CCBA8 -> VA 0x00DE0BA8
CAL_OFF, CAL_VA = 0x6CCBA8, 0x00DE0BA8
DELTA = CAL_VA - CAL_OFF
print("DELTA = 0x%X" % DELTA)

def off2va(o): return o + DELTA
def va2off(v): return v - DELTA

svc = [("titleutilities",0x6CCB80),("tencent",0x6CCB90),("teams",0x6CCB98),
       ("storage",0x6CCBA0),("profiles",0x6CCBA8),("pooledstorage",0x6CCBB4),
       ("messaging",0x6CCBC4),("matchmaking",0x6CCBD0),("marketplace",0x6CCBDC),
       ("eventlog",0x6CCBE8),("non_critical",0x6CCBF4),("critical",0x6CCC04)]

print("\n=== 服务名 VA ===")
for n,o in svc:
    print("  %-16s file 0x%X VA 0x%08X" % (n,o,off2va(o)))

print("\n=== 搜指向这些 VA 的 u32 指针 ===")
found = {}
for n,o in svc:
    va = off2va(o)
    ptr = struct.pack("<I", va)
    hits = []
    i = 0
    while True:
        p = data.find(ptr, i)
        if p < 0: break
        hits.append(p); i = p+1
    found[n] = hits
    print("  %-16s n=%d %s" % (n, len(hits), ["0x%X"%h for h in hits[:10]]))

# 找成组的指针(服务表)
allp = []
for n,hs in found.items():
    for h in hs: allp.append((h,n))
allp.sort()
print("\n=== 指针簇(间距<=0x40视为同表) ===")
cl=[]; cur=[]
for p,n in allp:
    if cur and p-cur[-1][0] > 0x40:
        cl.append(cur); cur=[]
    cur.append((p,n))
if cur: cl.append(cur)
for c in cl:
    if len(c)>=3:
        print("  @0x%X..0x%X (%d):" % (c[0][0],c[-1][0],len(c)))
        lo=c[0][0]-0x40; hi=c[-1][0]+0x40
        p=lo
        while p+4<=hi:
            v=struct.unpack_from("<I",data,p)[0]
            tag=""
            for n,o in svc:
                if v==off2va(o): tag=n
            print("    0x%06X: 0x%08X %s"%(p,v,tag))
            p+=4
