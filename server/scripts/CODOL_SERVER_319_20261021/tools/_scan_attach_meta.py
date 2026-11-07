import struct,re
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'
d=open(p,'rb').read(); base=0xfc24; n=8557
for i in range(n):
    t,off,ptr,sz=struct.unpack_from('<4I',d,base+i*16)
    if t!=43: continue
    b=d[off:off+sz]
    for pos in range(0, max(0,len(b)-12),4):
        if b[pos:pos+4]==b'\xff'*4:
            count=struct.unpack_from('<I',b,pos+4)[0]
            if count<=16 and b[pos+8:pos+12]==b'\xff'*4:
                e=b.find(b'\0',pos+12)
                name=b[pos+12:e].decode('latin1') if e>=0 else ''
                if name and all(32<=ord(c)<127 for c in name):
                    print(i,hex(off),hex(sz),'pos',hex(pos),'count',count,'name',name)
