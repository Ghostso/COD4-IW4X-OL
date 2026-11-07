import struct,json
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'
d=open(p,'rb').read(); j=json.load(open(r'fixtures\common_mp_weapondefs_20261023.json',encoding='utf-8'))
names={'rpgdragon_mp','frag_snowgrenade_mp','c4bomber_mp'}
for r in j['weapons']:
    if r['name'] in names:
        b=d[r['offset']:r['offset']+r['size']]
        print('\n',r['name'])
        for o in [0x778,0x77c,0x780,0x784,0x788,0x794,0x798,0x79c,0x7a4,0x7a8,0x7b4]:
            print(hex(o),struct.unpack_from('<i',b,o+0x330)[0],struct.unpack_from('<f',b,o+0x330)[0])
