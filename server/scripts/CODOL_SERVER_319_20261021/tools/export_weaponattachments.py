# -*- coding: utf-8 -*-
"""Index 3.19 weaponattach metadata from common_mp_zone.bin.

3.19 does not serialize the WeaponAttachment override array in the same shape
as the 1.1.1.13 reference.  This tool therefore only records fields that are
directly visible and checksummed:
  visible prefix bytes, metadata offset, count, inline name, and raw tail.
It deliberately does not invent {offset,type,value} records.
"""
from pathlib import Path
import json, struct, sys
ROOT=Path(r'D:\BaiduNetdiskDownload\使命召唤OL')
ZONE=ROOT/'run_codol_001'/'runs'/'PHASE7_STATIC_20261023'/'common_mp_zone.bin'
OUT=ROOT/'CODOL_SERVER_319_20261021'/'fixtures'/'common_mp_weaponattach_metadata_20261023.json'
DIR_OFF,DIR_COUNT,DIR_END=0xFC24,8557,0x312F4
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def cstr(b,o):
    e=b.find(b'\0',o)
    return (None,e) if e<0 else (b[o:e].decode('latin1'),e+1)
def printable(s): return bool(s) and all(32<=ord(c)<127 for c in s)
def find_meta(b):
    hits=[]
    for pos in range(0,min(len(b)-12,0x100),4):
        if b[pos:pos+4]==b'\xff'*4:
            count=u32(b,pos+4)
            if count<=64 and b[pos+8:pos+12]==b'\xff'*4:
                name,end=cstr(b,pos+12)
                if name is not None and printable(name): hits.append((pos,count,name,end))
    return hits
def main():
    d=ZONE.read_bytes()
    if DIR_OFF+DIR_COUNT*16!=DIR_END: raise SystemExit('directory constants inconsistent')
    rows=[]; unresolved=[]
    for i in range(DIR_COUNT):
        typ,off,ptr,size=struct.unpack_from('<4I',d,DIR_OFF+i*16)
        if typ!=43: continue
        b=d[off:off+size]; hits=find_meta(b)
        if not hits:
            unresolved.append({'index':i,'offset':off,'size':size}); continue
        for meta,count,name,end in hits:
            rows.append({'index':i,'asset_offset':off,'asset_size':size,'metadata_offset':meta,
                         'count':count,'name':name,'prefix_hex':b[:meta].hex(),
                         'tail_offset':end,'tail_hex':b[end:].hex(),'tail_size':len(b)-end})
    out={'zone':str(ZONE),'directory':{'offset':DIR_OFF,'count':DIR_COUNT,'end':DIR_END},
         'note':'metadata-only; 3.19 override tuple layout is not closed',
         'decoded_count':len(rows),'unresolved_count':len(unresolved),
         'attachments':sorted(rows,key=lambda r:r['name']),'unresolved':unresolved}
    OUT.write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding='utf-8')
    print('decoded',len(rows),'unresolved',len(unresolved),'wrote',OUT)
if __name__=='__main__':main()
