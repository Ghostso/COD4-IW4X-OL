import struct
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
def hexdump(va,n,label):
    o=va-BASE
    print("--- %s  %08X ---" % (label,va))
    for r in range(0,n,16):
        c=d[o+r:o+r+16]
        print("%08X  %-47s  %s" % (va+r," ".join("%02x"%b for b in c),"".join(chr(b) if 32<=b<127 else "." for b in c)))
hexdump(0xDC7360,0x100,"around vtable A")
