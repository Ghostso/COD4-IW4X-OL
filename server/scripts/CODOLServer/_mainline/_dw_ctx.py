import re
b=open(r"COD OL\codoMP_client_shipRetail.exe","rb").read()
def ctx(va, back=0, fwd=0x180):
    off = va - 0x714000
    seg=b[off-back:off+fwd]
    base=va-back
    print("=== around VA 0x%08X ==="%va)
    i=0
    while i<len(seg):
        j=i
        while j<len(seg) and 32<=seg[j]<127: j+=1
        if j-i>=3:
            print("  VA 0x%08X  %r"%(base+i, seg[i:j].decode("latin1")[:120]))
            i=j
        else: i+=1
ctx(0x00DDFFB0, 0x40)
ctx(0x00DDF6C8, 0x20)
