import struct
d=open(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin","rb").read()
base=0x400000
for t in (0x7EF271,0x7EF1C8,0x7EF266):
    out=[]
    for i in range(len(d)-5):
        if d[i]==0xe8:
            rel=struct.unpack_from("<i",d,i+1)[0]
            if base+i+5+rel==t: out.append(base+i)
    print(hex(t),[hex(x) for x in out])
