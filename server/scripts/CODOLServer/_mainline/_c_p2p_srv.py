import re
d=open(r"COD OL\IIPS\p2papp.dll","rb").read()
o=0x19A8C0
seg=d[o:o+0x600]
i=0
print("=== off 0x19A8C0 .. 0x19AEC0 ===")
while i<len(seg):
    j=i
    while j<len(seg) and 32<=seg[j]<127: j+=1
    if j-i>=3:
        print("  off 0x%06X %r"%(o+i, seg[i:j].decode("latin1")[:140]))
        i=j
    else: i+=1
print()
print("=== 所有 *.qq.com / *.qqlive / PEER_SERVER 串 ===")
for m in re.finditer(rb"[\x20-\x7e]{4,}", d):
    s=m.group().decode("latin1")
    if ("qq.com" in s) or ("PEER_SERVER" in s) or ("qqlive" in s) or ("tpt" in s):
        print("  off 0x%06X %r"%(m.start(), s[:140]))
