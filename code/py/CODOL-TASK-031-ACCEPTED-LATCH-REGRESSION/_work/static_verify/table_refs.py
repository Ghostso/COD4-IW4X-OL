import struct
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
targets=[0x632920,0x632930,0x632950,0x632A00,0x632680,0x62E9F0,0x62CA60,0x62C580,0x629730,0x6297A0,0x8435D0,0x850A40,0xA09910,0xDC73A0,0xDC73B0,0xDC7840,0xDC7850]
for t in targets:
    tb=struct.pack("<I",t); s=0; found=[]
    while True:
        i=d.find(tb,s)
        if i<0: break
        found.append(i+BASE); s=i+1
    print("%08X  refs(%d): %s" % (t,len(found), ", ".join("%08X"%a for a in found[:12])))
