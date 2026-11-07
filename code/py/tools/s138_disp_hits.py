import struct,sys
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
E=r"E:\codol_re\client_image_20261027.bin";VA=0x400000
d=open(E,"rb").read();N=len(d)
for disp in [0x188,0x18c,0x1d0,0x140,0x144]:
    pat=struct.pack("<I",disp)
    hits=[];i=0
    while True:
        i=d.find(pat,i)
        if i<0:break
        # look back for modrm 0x83/0x89/0x8b/0x85 style
        hits.append(VA+i);i+=1
    print("disp 0x%X: %d hits: %s"%(disp,len(hits),[hex(h) for h in hits[:40]]))
