#!/usr/bin/env python3
"""V=04/06/08 body 是否 dwRoomMessage 位流? 尝试多种起点解码(MSB), 打印 tag 序列看是否落在12标签词表.
   body 通用前缀 = 68 ab 5b ab 63 ab 03 ...
"""
import json, struct
CORPUS=r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
recs=json.load(open(CORPUS,"r",encoding="utf-8"))
if isinstance(recs,dict): recs=recs.get("records") or recs.get("data") or list(recs.values())
FIXED={0x01:1,0x03:1,0x06:2,0x07:4,0x08:4,0x09:8,0x0a:8}
def blobs(payload):
    out=[];i=0;n=len(payload)
    while i<n:
        t=payload[i];i+=1
        if t==0x00: continue
        if t==0x10:
            j=payload.find(b"\x00",i)
            if j<0: break
            i=j+1;continue
        if t in FIXED: i+=FIXED[t];continue
        if t in (0x13,0x6b,0x6c):
            if i>=n or payload[i]!=0x08: break
            i+=1
            if i+4>n:break
            ln=struct.unpack_from("<I",payload,i)[0];i+=4
            data=payload[i:i+ln];i+=ln
            if t in(0x6b,0x6c): i+=4
            if t==0x13: out.append(data)
            continue
        break
    return out
inner=[]
for r in recs:
    if r.get("svc")==11 and r.get("task")==4:
        for d in blobs(bytes.fromhex(r["payload"])):
            if len(d)>=4 and struct.unpack_from("<I",d,0)[0]==len(d)-4:
                inner.append(d[4:])

class BR:
    def __init__(s,b,o=0): s.b=b;s.pos=o;s.n=len(b)*8
    def bits(s,k):
        v=0
        for _ in range(k):
            if s.pos>=s.n: raise EOFError
            v=(v<<1)|((s.b[s.pos>>3]>>(7-(s.pos&7)))&1);s.pos+=1
        return v
WIDTH={0x01:1,0x02:8,0x03:8,0x05:16,0x06:16,0x07:32,0x08:32,0x0a:64,0x0d:32}
def dec(b,off,nsteps=40):
    br=BR(b,off);tags=[]
    try:
        for _ in range(nsteps):
            if br.n-br.pos<5: break
            t=br.bits(5);tags.append(t)
            if t in WIDTH: br.bits(WIDTH[t])
            elif t==0x15: tags.append('15');break
            elif t==0x10:
                while br.bits(8)!=0: pass
            elif t==0x13:
                if br.bits(5)!=8: tags.append('bad13');break
                br.bits(br.bits(32)*8)
            else: tags.append('bad%02x'%t);break
    except EOFError: tags.append('eof')
    return tags

# V=04 body 样本 (x[10:]) 前几条 distinct
for V in (4,6,8):
    xs=[x for x in inner if x and x[0]==2 and x[1]==V]
    x=sorted(set(xs),key=len)[0]
    body=x[10:]
    print("=== V=0x%02X  len=%d body[:20]=%s"%(V,len(x),body[:20].hex()))
    for off in [0,3,5,8]:
        print("   bitoff=%d : %s"%(off,dec(body,off)))
