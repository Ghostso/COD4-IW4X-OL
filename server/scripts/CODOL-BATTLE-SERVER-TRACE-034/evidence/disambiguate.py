import struct
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read()
BASE=0x400000
def count(v):
    tb=struct.pack("<I",v); n=0; s=0; first=[]
    while True:
        i=d.find(tb,s)
        if i<0: break
        n+=1
        if len(first)<6: first.append(i)
        s=i+1
    return n,first
print("Probe globals, tested three ways (raw RVA / VA-if-offset==VA / VA-if-offset==VA-0x400000):")
for name,rva in [("playerStateFields",0x855F70),("connectionState",0x162E7EC),
                 ("localClientIndex",0x7417BA8),("expectedConfigChecksum",0x29F7D90),
                 ("comError",0x197D20),("configChecksumCompare",0x6E06B)]:
    a=count(rva)              # value stays as RVA (offset==VA hypothesis has VA==RVA)
    b=count(rva)              
    c=count(BASE+rva)         # value is absolute VA (offset==VA-0x400000)
    print("  %-22s rva=%08X  as-is=%d  va(abs)=%d  first_abs=%s" % (name,rva,a[0],c[0],["%X"%x for x in c[1]]))
print()
print("Sanity: are there ANY 0xE8 rel32 in this file? (count first 1MB)")
n=sum(1 for i in range(0x100000) if d[i]==0xE8)
print("  E8 byte count in first 1MB:", n)
