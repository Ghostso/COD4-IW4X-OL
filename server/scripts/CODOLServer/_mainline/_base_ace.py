import re
p=r"COD OL\codoMP_client_shipRetailBase.dll"
d=open(p,"rb").read()
print("size",len(d))
for key in (b"SGuard", b"ace-ats32", b"ace-ats", b"AntiCheatExpert", b"ACE-"):
    i=0;h=[]
    while True:
        j=d.find(key,i)
        if j<0: break
        h.append(j); i=j+1
        if len(h)>8: break
    print("%-20r -> %s"%(key,[hex(x) for x in h]))
print()
for key in (b"SGuard", b"ace-ats32", b"AntiCheatExpert"):
    i=0
    while True:
        j=d.find(key,i)
        if j<0: break
        s=max(0,j-60); e=min(len(d),j+90)
        print("--- %r @ 0x%06X ---"%(key,j))
        seg=d[s:e]
        print("   ", repr(seg[:150]))
        i=j+1
        if i>j+1 and False: break
