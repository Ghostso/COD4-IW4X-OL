import struct, json, collections
root=r'D:\BaiduNetdiskDownload\使命召唤OL'
p=root+r'\_map_extract\coop_train_zone.bin'; d=open(p,'rb').read()
# found directory run (191 records) at 0x11c1
base=0x11c1; n=191
assets=[]
for i in range(n):
 t,off,ptr,sz=struct.unpack_from('<4I',d,base+i*16)
 assets.append((i,t,off,ptr,sz))
print('types',collections.Counter(t for _,t,_,_,_ in assets))
def cstr(b,o):
 e=b.find(b'\0',o)
 return None if e<0 else b[o:e].decode('latin1')
def header_name(t,b):
 if t==10: pos=36
 elif t==27: return None
 else:
  m={0:68,1:72,2:88,3:48,4:360,5:96,9:204,11:12,12:136,13:48,15:None,16:16,18:84,20:116,21:None,22:16,24:24,25:12,26:400,28:0xBFC,30:32,31:8,36:16,37:16,38:24,39:12,40:112,41:788,42:36,43:12}
  pos=m.get(t)
 if pos is None or len(b)<pos:return None
 return cstr(b,pos)
for i,t,off,ptr,sz in assets:
 blob=d[off:off+sz]
 nm=header_name(t,blob)
 if t in (28,43,36,44) or (nm and ('weapon' in nm.lower() or nm.lower().endswith('_mp'))):
  print(i,'type',t,'off',hex(off),'sz',hex(sz),'name',nm,'head',blob[:16].hex())
