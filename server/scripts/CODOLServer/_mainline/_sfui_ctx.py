d=open(r"COD OL\codoMP_client_shipRetail.exe","rb").read()
o=0x6C9800   # around VA 0x00AC9888
seg=d[o:o+0x600]
i=0
print("=== VA 0x00AC9800 - 0x00AC9E00 ===")
while i<len(seg):
    j=i
    while j<len(seg) and 32<=seg[j]<127: j+=1
    if j-i>=3:
        print("  VA 0x%08X  %r"%(0xAC9800+i, seg[i:j].decode("latin1")))
        i=j
    else: i+=1
