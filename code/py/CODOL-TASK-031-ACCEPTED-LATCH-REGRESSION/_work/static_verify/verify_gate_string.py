IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
for va in (0xDC69B0,0xDC69A8,0xDC69B8):
    o=va-BASE; end=d.find(b'\x00',o)
    print("%08X  %r" % (va, d[o:end]))
# what is right before 0xDC69B0 ?
o=0xDC6960-BASE
print("--- dump 0xDC6960..0xDC69E0 ---")
for r in range(0,0x80,16):
    c=d[o+r:o+r+16]
    print("%08X  %-47s %s" % (0xDC6960+r," ".join("%02x"%b for b in c),"".join(chr(b) if 32<=b<127 else "." for b in c)))
