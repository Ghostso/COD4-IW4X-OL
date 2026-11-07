import struct,json,collections
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'; d=open(p,'rb').read(); j=json.load(open(r'fixtures\common_mp_weapondefs_20261023.json',encoding='utf-8'))
names={'rpgdragon_mp','frag_snowgrenade_mp','c4bomber_mp'}
blobs={}
for r in j['weapons']:
    if r['name'] in names: blobs[r['name']]=d[r['offset']:r['offset']+r['size']]
for name,b in blobs.items():
    print('\n',name)
    for v in [64,80,96,100,120,128,150,180,200,220,250,256,300,350,400,500,600,700,800,900,1000,1200,1500,2000,3000]:
        hit=[]
        for o in range(0,min(len(b)-4,0x2000)):
            if struct.unpack_from('<i',b,o)[0]==v: hit.append(hex(o))
        if hit: print(v,hit[:20])
