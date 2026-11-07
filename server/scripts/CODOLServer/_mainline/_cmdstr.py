import re
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read(); base=0x400000
print("=== 0x7F8A00-0x800000 区间字符串（0x77F8B3 附近模块）===")
o=0x77F000-base
seg=d[o:o+0x4000]; i=0
n=0
while i<len(seg) and n<80:
    j=i
    while j<len(seg) and 32<=seg[j]<127: j+=1
    if j-i>=4:
        print("   0x%08X %r"%(0x77F000+i, seg[i:j].decode("latin1")[:100])); n+=1; i=j
    else: i+=1
