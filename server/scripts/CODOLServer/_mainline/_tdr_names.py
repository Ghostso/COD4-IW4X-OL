import re
p=r"COD OL\GDPOpenProtocol.tdr"
d=open(p,"rb").read()
# TDR 通常是 "名字\0类型\0字段..." 的形式，尝试提取所有可见名字
names=[]
for m in re.finditer(rb"[A-Za-z_][A-Za-z0-9_]{2,60}", d):
    s=m.group().decode("latin1")
    names.append(s)
import collections
c=collections.Counter(names)
print("唯一标识符数:", len(c))
print()
print("=== 含 Qos/QOS/SS/GS/Token 的 ===")
for n,k in c.most_common():
    if any(x in n for x in ("Qos","QOS","Tss","TSS","SS","Token","Uin","UIN")):
        print("   %-40s x%d"%(n,k))
