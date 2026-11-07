import struct
p=r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\coop_train_zone.bin'; d=open(p,'rb').read()
delta=0x30069e8d-0x23f5a4
vals={
'planes':0x23f5a4,'materials':0x23f7f0,'mat0':0x23f7f0,'mat1':0x23f7fc,'mat2':0x23f80c,'mat3':0x23f816,
'sides':0x23f81b,'edges':0x23f8f3,'data_fc50':0x23fc50,
}
print('delta',hex(delta))
for name,off in vals.items():
 a=off+delta; occ=[]; start=0
 while True:
  i=d.find(struct.pack('<I',a),start)
  if i<0: break
  occ.append(i); start=i+1
 print(name,hex(off),'->',hex(a),'occ',len(occ),[hex(x) for x in occ[:50]])
