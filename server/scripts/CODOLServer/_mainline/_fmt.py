d=open(r"COD OL\codoMP_client_shipRetail.exe","rb").read()
o=0x6B0000
seg=d[o:o+0x200]
i=0
print("=== 0x6B0000 附近 ===")
while i<len(seg):
    j=i
    while j<len(seg) and 32<=seg[j]<127: j+=1
    if j-i>=3:
        print("  off 0x%06X  %r"%(o+i, seg[i:j].decode("latin1")))
        i=j
    else: i+=1
print()
print("=== 0x6C6B54 / 0x6C6D2F 附近 ===")
for base in (0x6C6B00, 0x6C6D00):
    seg=d[base:base+0x80]; i=0
    print("--- off 0x%06X ---"%base)
    while i<len(seg):
        j=i
        while j<len(seg) and 32<=seg[j]<127: j+=1
        if j-i>=3:
            print("    off 0x%06X  %r"%(base+i, seg[i:j].decode("latin1"))); i=j
        else: i+=1
