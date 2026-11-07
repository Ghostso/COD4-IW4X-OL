import re
p=r"COD OL\GDPOpenProtocol.tdr"
d=open(p,"rb").read()
print("size",len(d),"head",d[:32].hex())
# 找 TssQosPkg 及相关
for key in (b"TssQosPkg", b"QosPkg", b"TQos", b"Qos", b"Tss", b"TssQos"):
    i=0;h=[]
    while True:
        j=d.find(key,i)
        if j<0: break
        h.append(j); i=j+1
        if len(h)>8: break
    print("%-12r -> %s"%(key,[hex(x) for x in h]))
print()
print("=== TssQosPkg 附近上下文 ===")
for j in [m.start() for m in re.finditer(rb"TssQos", d)][:4]:
    s=max(0,j-160); e=min(len(d),j+260)
    seg=d[s:e]
    print("--- off 0x%06X ---"%j)
    i=0
    while i<len(seg):
        k=i
        while k<len(seg) and 32<=seg[k]<127: k+=1
        if k-i>=3: print("    %r"%seg[i:k].decode("latin1")); i=k
        else: i+=1
