import re
b=open(r"COD OL\codoMP_client_shipRetail.exe","rb").read()
print("=== 所有 QOS_SS_* / QOS* 定义 ===")
for m in re.finditer(rb"QOS[A-Za-z0-9_]{2,40}", b):
    print("  VA 0x%08X  %s" % (0x714000+m.start(), m.group().decode("latin1")))
print()
print("=== VA 0x00E43D00 .. 0x00E44500 区域全串 ===")
off=0x00E43D00-0x714000
seg=b[off:off+0x800]
i=0
while i<len(seg):
    j=i
    while j<len(seg) and 32<=seg[j]<127: j+=1
    if j-i>=3:
        print("  VA 0x%08X  %r"%(0x00E43D00+i, seg[i:j].decode("latin1")[:120])); i=j
    else: i+=1
