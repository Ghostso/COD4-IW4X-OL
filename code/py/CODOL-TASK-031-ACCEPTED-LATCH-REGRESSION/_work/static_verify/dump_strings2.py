import capstone, struct
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
def hexdump(va,n):
    o=va-BASE
    print("--- %08X ---"%va)
    for r in range(0,n,16):
        c=d[o+r:o+r+16]
        print("%08X  %-47s  %s"%(va+r," ".join("%02x"%b for b in c),"".join(chr(b) if 32<=b<127 else "." for b in c)))
# what is at the arg pushed at 0x6326DA -> 0xDC69B0 "mmbook accepted"; also check 0xDC74F8, 0xDC751C
for va,n in [(0xDC74F8,0x40),(0xDC751C,0x30),(0xDC7594,0x30),(0xDC67C4,0x40)]:
    hexdump(va,n)
