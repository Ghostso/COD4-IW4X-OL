IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
def s(va,n=64):
    o=va-BASE; end=d.find(b'\x00',o); return d[o:min(end,o+n)]
for va in (0xDC69B0,0xDC69C0,0xDC69D4,0xDDA6D0,0xDDA6E4,0xDDA6F4,0xDBB314,0xDBB300,0xDB8B48,0xDB468C,0xDC5864,0xDDA6D0):
    print("%08X  %r" % (va, s(va)))
