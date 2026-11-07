import struct,json
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'
d=open(p,'rb').read(); base=0xfc24; n=8557; A=0x28
j=json.load(open(r'fixtures\common_mp_weapondefs_20261023.json',encoding='utf-8'))
fields={'clip_size':0xe68,'fire_time_ms':0xe70,'reload_ms':0x884,'reload_empty_ms':0x890,'reload_add_ms':0x898,'damage':0xd10,'player_damage':0xd14,'min_damage':0xd18,'min_player_damage':0xd1c,'max_damage_range':0xd28,'min_damage_range':0xd30,'move_speed_scale':0x9a0,'ads_move_speed_scale':0x9a4,'sprint_duration_scale':0x9a8}
for r in j['firingrange']:
    key=('SF_WEAPON_'+r['name'][:-3].upper()+'_MP_NAME').encode()
    for i in range(n):
        t,off,ptr,sz=struct.unpack_from('<4I',d,base+i*16)
        if t!=28: continue
        b=d[A+off:A+off+sz]
        if key in b:
            print('\n',r['name'],'actual',hex(A+off),'size',hex(sz))
            for k,o in fields.items():
                if o+4<=len(b):
                    if k in ('max_damage_range','min_damage_range','move_speed_scale','ads_move_speed_scale','sprint_duration_scale'): v=struct.unpack_from('<f',b,o)[0]
                    else: v=struct.unpack_from('<i',b,o)[0]
                    print(k,'json',r[k],'actual',v,'off',hex(o))
            break
