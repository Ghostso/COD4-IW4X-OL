#!/usr/bin/env python3
"""看 0x35BB180-0x35BB340 精确上下文: DWServiceStatus 服务名清单。"""
E = r"E:\codol_re\client_image_20261027.bin"
data = open(E, "rb").read()
def show(lo,hi,label):
    print("=== %s 0x%X-0x%X ==="%(label,lo,hi))
    for i in range(lo,hi,16):
        c=data[i:i+16]
        print("  0x%08X  %-47s  %s"%(i," ".join("%02x"%b for b in c),
              "".join(chr(b) if 32<=b<127 else "." for b in c)))
    print()
show(0x35BB180,0x35BB340,"DWServiceStatus ctx")

# 找所有 'DWServiceStatus' 出现处, 并 dump 前后
print("=== all 'DWServiceStatus' occurrences ===")
i=0
while True:
    p=data.find(b"DWServiceStatus",i)
    if p<0: break
    print("  @0x%X"%p)
    i=p+1

# 找 AS3 中可能的服务名清单: 搜 'leaderboard','matchmaking','messaging','party','clan' 作为 len-prefixed 串
print("\n=== len-prefixed service-name candidates in AS3 area (0x3000000-0x3700000) ===")
names=[b"leaderboard",b"matchmaking",b"messaging",b"party",b"clan",b"marketplace",
       b"storage",b"profiles",b"eventlog",b"titleutilities",b"tencent",b"teams",
       b"publisher_storage",b"pooledstorage",b"richpresence",b"presence"]
for nm in names:
    pat=bytes([len(nm)])+nm
    i=0;hits=[]
    while True:
        p=data.find(pat,i)
        if p<0: break
        if 0x3000000<=p<0x3700000: hits.append(p)
        i=p+1
        if len(hits)>=8: break
    if hits:
        print("  %-20s %s"%(nm.decode(),["0x%X"%h for h in hits]))
