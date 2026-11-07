import struct,sys
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
E=r"E:\codol_re\client_image_20261027.bin";VA=0x400000
d=open(E,"rb").read();N=len(d)
for pat in [b"\xbc\xa0\x03\x00", b"\xb8\xa0\x03\x00", b"\xc4\xa0\x03\x00", b"\xc0\xa0\x03\x00"]:
    hits=[];i=0
    while True:
        i=d.find(pat,i)
        if i<0:break
        hits.append(VA+i);i+=1
    print(pat.hex(), len(hits), [hex(h) for h in hits[:20]])
