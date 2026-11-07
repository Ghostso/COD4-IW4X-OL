import struct
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
def occ(v, width=4):
    tb=struct.pack("<I",v&0xffffffff); s=0; out=[]
    while True:
        i=d.find(tb,s)
        if i<0: break
        out.append(i); s=i+1
    return out
print("=== netchan signature constants (as 32-bit immediates) ===")
for v,name in [(0x1FFFFFFF,"NetchanSequenceMask"),(0x1154-0,"FragmentSize 1154"),(0x482,"0x482=1154"),
               (0x20000,"MaxFragmentMessage 0x20000"),(0x80000000,"0x80000000"),(0x40000000,"0x40000000"),
               (0x20000000,"0x20000000"),(128,"MaxFragments 128")]:
    o=occ(v)
    print("  %-26s 0x%08X : %d occurrence(s) %s" % (name, v&0xffffffff, len(o), ["%X"%x for x in o[:8]]))
print()
print("=== 16-bit 1154 occurrences (lea/cmp imm16) ===")
tb=struct.pack("<H",1154); s=0; o=[]
while True:
    i=d.find(tb,s)
    if i<0: break
    o.append(i); s=i+1
print("  count=%d  %s" % (len(o), ["%X"%x for x in o[:20]]))
print()
print("=== 10-bit / fragment header  size 0x0A occurrences near netchan-like code ===")
print("  (informational)")
