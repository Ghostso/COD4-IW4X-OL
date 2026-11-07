import struct
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
def scan(t):
    tb=struct.pack("<I",t); s=0; out=[]
    while True:
        i=d.find(tb,s)
        if i<0: break
        out.append(i+BASE); s=i+1
    return out
for t in (0xDC6800,0xDC69C0,0xDC73A0,0xDC7360,0xDC7840):
    r=scan(t)
    print("%08X: %s" % (t, ", ".join("%08X"%a for a in r[:20]) or "NONE"))
