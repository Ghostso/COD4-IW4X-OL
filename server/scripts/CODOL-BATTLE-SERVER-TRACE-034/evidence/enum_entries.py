IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
def entries(lo,hi):
    out=[]
    for p in range(lo,hi):
        if d[p-1]==0xCC:
            if d[p:p+3]==b"\x55\x8b\xec" or d[p:p+3]==b"\x6a\xff" or d[p:p+2]==b"\x8b\xff":
                out.append(p)
    return out
for lo,hi,label in [(0x6C000,0x70000,"msg/parse family (probe 0x6xxxx)"),
                    (0x1A0000,0x1A6000,"delta/bit family (probe 0x1Axxxx)"),
                    (0x5F000,0x62000,"type dispatch + OOB region")]:
    e=entries(lo,hi)
    print("=== %s : %d function entries (offset/RVA) ===" % (label,len(e)))
    print("   " + " ".join("%X"%x for x in e))
    print()
