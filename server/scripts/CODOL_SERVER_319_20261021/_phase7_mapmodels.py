import struct,re,json
root=r'D:\BaiduNetdiskDownload\使命召唤OL'
p=root+r'\_map_extract\coop_train_zone.bin'; d=open(p,'rb').read()
bounds_off=0x24008b
ents=[]; s=open(root+r'\_map_extract\coop_train_entities.txt',encoding='utf-8').read()
for block in re.findall(r'\{[^{}]*\}',s,re.S):
 if 'script_brushmodel' in block:
  kv=dict(re.findall(r'"([^"]+)"\s+"([^"]*)"',block)); model=int(kv['model'][1:]); origin=tuple(map(float,kv['origin'].split()))
  bi=model-70
  mid=struct.unpack_from('<3f',d,bounds_off+bi*24); half=struct.unpack_from('<3f',d,bounds_off+bi*24+12)
  wm=tuple(origin[i]+mid[i] for i in range(3))
  ents.append((model,origin,bi,wm,half,kv.get('targetname','')))
for e in ents:
 print(e[0], 'origin',e[1],'brush',e[2],'worldmid',tuple(round(x,3) for x in e[3]),'half',tuple(round(x,3) for x in e[4]),e[5])
print('spawn within any?')
sp=(48,-572,-116)
for e in ents:
 wm,h=e[3],e[4]
 if all(abs(sp[i]-wm[i])<=h[i]+32 for i in range(3)): print('near',e)
