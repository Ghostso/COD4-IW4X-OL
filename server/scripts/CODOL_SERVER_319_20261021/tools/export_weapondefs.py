# -*- coding: utf-8 -*-
"""Extract CODOL 3.19 WeaponDef metadata from common_mp_zone.bin.

Zone-verified fields only. Runtime/OLFinal candidates are recorded separately
as unverified provenance and never mixed into emitted weapon values.
"""
from pathlib import Path
import json, re, struct, sys

ROOT=Path(r'D:\BaiduNetdiskDownload\使命召唤OL')
DEFAULT_ZONE=ROOT/'run_codol_001'/'runs'/'PHASE7_STATIC_20261023'/'common_mp_zone.bin'
OUT=ROOT/'CODOL_SERVER_319_20261021'/'fixtures'/'common_mp_weapondefs_20261023.json'
INC=ROOT/'CODOL_SERVER_319_20261021'/'include'/'codol_weapondefs_firingrange.inc'
FIRINGRANGE={'ak47_mp','mp5k_mp','cheytac_mp','ak104_mp','ump45_mp','as50_mp','m4a1tech_mp','aks74u_mp','m21ebr_mp','scarsapr_mp','mp5sd_mp','l115_mp','an94_mp','p90_mp','msr_mp','m1garand_mp','miniuzi_mp','rsrt3_mp'}
DIR_OFF,DIR_COUNT,DIR_END=0xFC24,8557,0x312F4
ASSET_BASE=0x28
KEY_RE=re.compile(rb'SF_WEAPON_([A-Z0-9_]+)_MP_NAME')
NAME_RE=re.compile(rb'SF_WEAPON_([A-Z0-9_]+)_NAME')

ZONE_FIELDS={
    'clip_size':(0xE68,'i'),'fire_time_ms':(0xE70,'i'),
    'reload_ms':(0x85C,'i'),'reload_empty_ms':(0x868,'i'),'reload_add_ms':(0x870,'i'),
    'damage':(0xD10,'i'),'player_damage':(0xD14,'i'),'min_damage':(0xD18,'i'),'min_player_damage':(0xD1C,'i'),
    'max_damage_range':(0xD28,'f'),'min_damage_range':(0xD30,'f'),
    'move_speed_scale':(0x978,'f'),'ads_move_speed_scale':(0x97C,'f'),'sprint_duration_scale':(0x980,'f'),
    'location_damage_multipliers':(0xD4C,'f20'),
    'damage_tiers':(0xD10,'i6'),
    'damage_ranges':(0xD28,'f6'),
}

RUNTIME_WEAPONDEF_LAYOUT_UNVERIFIED={
    'hip_spread_stand_min':0x810,'hip_spread_stand_max':0x814,
    'hip_spread_ducked_min':0x818,'hip_spread_ducked_max':0x81C,
    'hip_spread_prone_min':0x820,'hip_spread_prone_max':0x824,
    'ads_spread':0xAC0,
    'old_curve_candidate':0xBB4,
    'old_hitloc_candidate':0xBF0,
}

def i32(b,o): return struct.unpack_from('<i',b,o)[0]
def f32(b,o): return struct.unpack_from('<f',b,o)[0]
def name_from_blob(b):
    m=KEY_RE.search(b)
    if m:return m.group(1).decode('ascii').lower()+'_mp'
    m=NAME_RE.search(b)
    return m.group(1).decode('ascii').lower() if m else None

def extract(path):
    d=path.read_bytes()
    if DIR_OFF+DIR_COUNT*16!=DIR_END: raise SystemExit('directory constants inconsistent')
    out=[]
    for i in range(DIR_COUNT):
        typ,off,ptr,size=struct.unpack_from('<4I',d,DIR_OFF+i*16)
        if off+size>len(d): raise SystemExit('asset exceeds zone')
        if typ!=28: continue
        b=d[ASSET_BASE+off:ASSET_BASE+off+size]; name=name_from_blob(b)
        if name is None:
            out.append({'index':i,'offset':off,'size':size,'name':None,'status':'name-unresolved'}); continue
        rec={'index':i,'offset':off,'size':size,'name':name}
        for k,(o,t) in ZONE_FIELDS.items():
            if t=='i': rec[k]=i32(b,o)
            elif t=='f': rec[k]=f32(b,o)
            elif t=='i6': rec[k]=[i32(b,o+4*j) for j in range(6)]
            elif t=='f6': rec[k]=[f32(b,o+4*j) for j in range(6)]
            else: rec[k]=[f32(b,o+4*j) for j in range(20)]
        rec['status']='verified-offset' if 0<=rec['clip_size']<=4096 and 0<=rec['fire_time_ms']<=10000 else 'field-range-suspect'
        out.append(rec)
    return out

def emit_inc(rows):
    lines=[]
    for r in sorted(rows,key=lambda x:x['name']):
        vals=', '.join('%.7ff'%x for x in r['location_damage_multipliers'])
        dt=', '.join(str(x) for x in r['damage_tiers'])
        dr=', '.join('%.7ff'%x for x in r['damage_ranges'])
        lines.append('  {"%s", %d, %d, %d, %d, %d, %d, %d, %d, %d, %.7ff, %.7ff, %.7ff, %.7ff, %.7ff, {%s}, {%s}, {%s}},'%(
            r['name'],r['clip_size'],r['fire_time_ms'],r['reload_ms'],r['reload_empty_ms'],r['reload_add_ms'],
            r['damage'],r['player_damage'],r['min_damage'],r['min_player_damage'],r['max_damage_range'],r['min_damage_range'],
            r['move_speed_scale'],r['ads_move_speed_scale'],r['sprint_duration_scale'],vals,dt,dr))
    INC.write_text('\n'.join(lines)+'\n',encoding='utf-8')

def main():
    path=Path(sys.argv[1]) if len(sys.argv)>1 else DEFAULT_ZONE
    records=extract(path); named=[r for r in records if r['name']]
    firing=sorted([r for r in named if r['name'] in FIRINGRANGE],key=lambda r:r['name'])
    res={'zone':str(path),'directory':{'offset':DIR_OFF,'count':DIR_COUNT,'end':DIR_END},
         'type28_count':len(records),'named_count':len(named),'firingrange_count':len(firing),
         'zone_verified_offsets':{k:v[0] for k,v in ZONE_FIELDS.items()},
         'runtime_weapondef_layout_unverified':RUNTIME_WEAPONDEF_LAYOUT_UNVERIFIED,
         'firingrange':firing,'weapons':sorted(named,key=lambda r:r['name']),
         'unresolved':[r for r in records if not r['name']]}
    OUT.write_text(json.dumps(res,indent=2,ensure_ascii=False),encoding='utf-8')
    emit_inc(firing)
    print('type28',len(records),'named',len(named),'firingrange',len(firing))
    print('wrote',OUT); print('wrote',INC)

if __name__=='__main__': main()
