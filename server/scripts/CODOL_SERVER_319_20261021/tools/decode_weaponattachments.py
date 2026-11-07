# -*- coding: utf-8 -*-
"""Decode the 3.19 weaponattach payload as the C1 0xAF0790 3->4 sextet stream.

0xAF0790 consumes 3 input bytes and emits 4 characters from
"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/",
padding with '=' for 1/2-byte tails.  This is not RFC base64: the source
stream is arbitrary binary and the EOF padding convention must be inferred.
The decoder below is the exact inverse for complete 3-byte groups and records
partial tails rather than silently padding bytes.
"""
from pathlib import Path
import struct, json, sys

ROOT=Path(r'D:\BaiduNetdiskDownload\使命召唤OL')
ZONE=ROOT/'run_codol_001'/'runs'/'PHASE7_STATIC_20261023'/'common_mp_zone.bin'
OUT=ROOT/'CODOL_SERVER_319_20261021'/'fixtures'/'common_mp_weaponattach_decoded_20261023.json'
BASE=0xFC24; COUNT=8557; ASSET_BASE=0x28
ALPH=b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
IDX={c:i for i,c in enumerate(ALPH)}

def decode(payload):
    out=bytearray(); pos=0; tail=b''
    while pos+4<=len(payload):
        q=payload[pos:pos+4]
        if any(c not in IDX for c in q):
            break
        a,b,c,d=(IDX[x] for x in q)
        if d==0x3f and c==0x3f: # not direct alphabet; only '=' handled below
            pass
        v=(a<<18)|(b<<12)|(c<<6)|d
        out.extend(((v>>16)&255,(v>>8)&255,v&255))
        pos+=4
    if pos<len(payload):
        tail=payload[pos:]
    return bytes(out),tail,pos

def main():
    d=ZONE.read_bytes(); rows=[]; ok=0; bad=[]
    for i in range(COUNT):
        t,off,ptr,sz=struct.unpack_from('<4I',d,BASE+i*16)
        if t!=43: continue
        b=d[ASSET_BASE+off:ASSET_BASE+off+sz]
        if len(b)<12:
            bad.append((i,'short')); continue
        nr,cnt,er=struct.unpack_from('<III',b,0)
        if nr!=0xffffffff:
            bad.append((i,'name-ref')); continue
        e=b.find(b'\0',12)
        if e<0:
            bad.append((i,'name-eof')); continue
        name=b[12:e].decode('latin1','replace'); payload=b[e+1:]
        dec,tail,used=decode(payload)
        rows.append({'index':i,'offset':off,'size':sz,'name':name,'count':cnt,
                     'payload_len':len(payload),'decoded_len':len(dec),'used':used,
                     'tail_hex':tail.hex(),'decoded_hex':dec.hex()})
        if not tail: ok+=1
    OUT.write_text(json.dumps({'zone':str(ZONE),'asset_base':ASSET_BASE,'decoded_rows':len(rows),'complete_rows':ok,'rows':rows,'bad':bad},indent=2,ensure_ascii=False),encoding='utf-8')
    print('rows',len(rows),'complete',ok,'bad',len(bad))
    for r in rows[:30]: print(r['name'],'count',r['count'],'payload',r['payload_len'],'decoded',r['decoded_len'],'tail',r['tail_hex'][:32])
    print('wrote',OUT)
if __name__=='__main__': main()
