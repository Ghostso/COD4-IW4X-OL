import struct,json,collections
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'
d=open(p,'rb').read(); base=0xfc24;n=8557
rows=[]
for i in range(n):
    t,off,ptr,sz=struct.unpack_from('<4I',d,base+i*16)
    if t!=43: continue
    b=d[off:off+sz]
    found=None
    for pos in range(0,max(0,len(b)-12),4):
        if b[pos:pos+4]==b'\xff'*4:
            cnt=struct.unpack_from('<I',b,pos+4)[0]
            if cnt<=64 and b[pos+8:pos+12]==b'\xff'*4:
                e=b.find(b'\0',pos+12)
                if e>=0:
                    name=b[pos+12:e].decode('latin1','replace')
                    if name and all(32<=ord(c)<127 for c in name):
                        found=(pos,cnt,name,e+1);break
    if found:
        pos,cnt,name,end=found; tail=sz-end
        rows.append((name,cnt,tail,pos,sz,b[end:].hex()))
print('rows',len(rows))
for k,v in collections.Counter((r[1],r[2]) for r in rows).most_common(30): print('count,tail',k,'n',v)
for r in rows:
    if r[0] in ['fmj_base','highcal_base','flashhider_base','scope_none','acog_base','silencer_m4','heartbeat_base','akimbo_base']:
        print(r)
