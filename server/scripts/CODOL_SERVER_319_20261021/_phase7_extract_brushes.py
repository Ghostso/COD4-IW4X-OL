import struct, math, json, os
ROOT=r'D:\BaiduNetdiskDownload\使命召唤OL'
p=ROOT+r'\_map_extract\coop_train_zone.bin'
d=open(p,'rb').read()
# Known, self-checked offsets for coop_train_mp_firingrange layout.
hdr=0x23f564; planes_off=0x23f5a4; nplanes=27
mats_off=0x23f7c0; nmats=4
strings_off=0x23f7f0
sides_off=0x23f81c; nsides=27
edges_off=0x23f8f4; nedges=144
leafnodes_off=0x23f983; nleafnodes=30
brushes_off=0x23fc53; nbrushes=30
bounds_off=0x24008b
contents_off=0x24035b
planes=[]
for i in range(nplanes):
 o=planes_off+i*20
 n=struct.unpack_from('<3f',d,o); dist=struct.unpack_from('<f',d,o+12)[0]; typ=d[o+16]
 planes.append({'normal':n,'dist':dist,'type':typ})
mats=[]
for i in range(nmats):
 o=mats_off+i*12
 surf,cont=struct.unpack_from('<ii',d,o+4)
 mats.append({'surface':surf,'contents':cont})
sides=[]
for i in range(nsides):
 o=sides_off+i*8
 ptr=struct.unpack_from('<I',d,o)[0]
 plane=(ptr-(planes_off+(0x30069e8d-0x23f5a4)))//20
 mat,adj,ec=struct.unpack_from('<Hbb',d,o+4)
 sides.append({'plane':plane,'material':mat,'adj':adj,'edge':ec})
# brush records
brushes=[]
for i in range(nbrushes):
 o=brushes_off+i*36
 ns,glass=struct.unpack_from('<HH',d,o); sp=struct.unpack_from('<I',d,o+4)[0]; ba=struct.unpack_from('<I',d,o+8)[0]
 si=None if sp==0 else (sp-(sides_off+(0x30069e8d-0x23f5a4)))//8
 brushes.append({'numsides':ns,'sides':si,'baseAdj':None if ba==0 else 'edge','raw':d[o:o+36].hex()})
bounds=[]
for i in range(nbrushes):
 mid=struct.unpack_from('<3f',d,bounds_off+i*24); half=struct.unpack_from('<3f',d,bounds_off+i*24+12)
 bounds.append({'mid':mid,'half':half})
contents=[struct.unpack_from('<i',d,contents_off+i*4)[0] for i in range(nbrushes)]
print('planes',len(planes),'sides',len(sides),'brushes',len(brushes))
for i,b in enumerate(brushes):
 print(i,b,'bounds',bounds[i],'contents',hex(contents[i]&0xffffffff))
