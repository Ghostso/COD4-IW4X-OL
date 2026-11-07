import re
d=open(r"COD OL\codoMP_client_shipRetail.exe","rb").read()
print("=== exe 里 ied-tqos 周边字符串 (VA 0x00DC5800 .. 0x00DC5A00) ===")
o=0x6C5800
seg=d[o:o+0x300]
i=0
while i<len(seg):
    j=i
    while j<len(seg) and 32<=seg[j]<127: j+=1
    if j-i>=3:
        print("  VA 0x%08X  %r"%(0x400000+o+i, seg[i:j].decode("latin1")))
        i=j
    else: i+=1
