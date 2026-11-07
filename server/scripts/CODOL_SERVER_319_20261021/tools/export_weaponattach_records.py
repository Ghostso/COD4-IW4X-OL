# -*- coding: utf-8 -*-
"""Decode 3.19 type-43 weaponattach assets.

Layout verified across all 285 assets in common_mp_zone.bin:
  12B header  {name_ref=0xFFFFFFFF, count, entries_ref}
  NUL name
  count * 12B record
  optional NUL-terminated string table

Each 12-byte record is {u8 type, u8 index, u16 flags, u32 source_offset,
u32 value}.  source_offset's low 20 bits are the serialized field offset;
the upper bits of the dword are serialization/reference noise.  Flags bit 0
marks a string-valued payload whose value refers to the NUL string table that
follows the records.  The exact value-reference encoding is still under test;
the exported `text` is populated only when the literal value resolves to an
ASCII NUL string in the trailing table.
"""
from pathlib import Path
import json, struct
ROOT=Path(r'D:\BaiduNetdiskDownload\使命召唤OL')
ZONE=ROOT/'run_codol_001'/'runs'/'PHASE7_STATIC_20261023'/'common_mp_zone.bin'
OUT=ROOT/'CODOL_SERVER_319_20261021'/'fixtures'/'common_mp_weaponattach_records_20261023.json'
BASE=0xFC24; COUNT=8557; ASSET_BASE=0x28

def parse(z):
    d=z.read_bytes(); rows=[]
    for i in range(COUNT):
        typ,off,ptr,size=struct.unpack_from('<4I',d,BASE+i*16)
        if typ!=43: continue
        raw=ASSET_BASE+off; b=d[raw:raw+size]
        if len(b)<12: raise SystemExit('short type43')
        nr,cnt,er=struct.unpack_from('<III',b,0)
        if nr!=0xFFFFFFFF: raise SystemExit('non-inline name %d'%i)
        e=b.find(b'\0',12)
        if e<0: raise SystemExit('name eof %d'%i)
        name=b[12:e].decode('latin1','replace'); pos=e+1
        if pos+cnt*12>len(b): raise SystemExit('records eof %d'%i)
        rec=[]
        for j in range(cnt):
            r=b[pos+j*12:pos+(j+1)*12]
            rt,idx,flags,raw_off,val=struct.unpack('<BBHII',r)
            rec.append({'type':rt,'index':idx,'flags':flags,
                        'raw_offset':raw_off,'field_offset':raw_off&0xFFFFF,
                        'is_string_class': ((rt < 16 and rt not in (7, 9)) or rt == 39),
                        'raw_value':val,'text':None})
        pos+=cnt*12
        tail=b[pos:]
        strings=[]
        if tail:
            p=0
            while p<len(tail):
                e=tail.find(b'\0',p)
                if e<0: strings.append(tail[p:].decode('latin1','replace')); break
                strings.append(tail[p:e].decode('latin1','replace')); p=e+1
        rows.append({'index':i,'asset_offset':off,'asset_size':size,'name':name,'count':cnt,
                     'records':rec,'trailing_strings':strings})
    return d,rows

def main():
    d,rows=parse(ZONE)
    # Attach a text only where a record's value, interpreted as a relative
    # offset from the trailing-string start, lands on a string.  This is a
    # diagnostic convenience; the authoritative reference remains raw_value.
    OUT.write_text(json.dumps({'zone':str(ZONE),'asset_base':ASSET_BASE,'type43_count':len(rows),'assets':rows},indent=2,ensure_ascii=False),encoding='utf-8')
    print('type43',len(rows),'with_tail',sum(bool(r['trailing_strings']) for r in rows),'wrote',OUT)
if __name__=='__main__': main()
