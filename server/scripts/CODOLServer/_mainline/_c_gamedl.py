import re
d=open(r"COD OL\IIPS\p2papp.dll","rb").read()
o=0x19AE90
seg=d[o:o+0x400]
i=0
print("=== off 0x19AE90 .. ===")
while i<len(seg):
    j=i
    while j<len(seg) and 32<=seg[j]<127: j+=1
    if j-i>=3:
        print("  off 0x%06X %r"%(o+i, seg[i:j].decode("latin1")[:140]))
        i=j
    else: i+=1
print()
# gamedl 相关全部
print("=== 含 gamedl 的串（全文件）===")
for m in re.finditer(rb"[\x20-\x7e]{4,}", d):
    s=m.group().decode("latin1")
    if "gamedl" in s or "gamedl" in s.lower():
        print("  off 0x%06X %r"%(m.start(), s[:140]))
