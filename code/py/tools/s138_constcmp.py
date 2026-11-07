import struct,sys
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
E=r"E:\codol_re\client_image_20261027.bin";VA=0x400000
d=open(E,"rb").read()
for name,v in [("accountID",0xE7C8A98A6B4C2D0E),("magicC",0x1122334455667788),("secondId",0x42706516032933CB),("magicB",0x8D51E398),("build",1649370)]:
    lo=v&0xffffffff; hi=(v>>32)&0xffffffff
    for tag,pat in [("lo",struct.pack("<I",lo)),("hi",struct.pack("<I",hi)),("u64",struct.pack("<Q",v))]:
        hits=[];i=0
        while True:
            i=d.find(pat,i)
            if i<0:break
            hits.append(VA+i);i+=1
        print("%-10s %-12s %-3s n=%d %s"%(name,hex(v),tag,len(hits),[hex(h) for h in hits[:12]]))
