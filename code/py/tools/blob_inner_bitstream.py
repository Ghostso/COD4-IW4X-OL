#!/usr/bin/env python3
"""判 11/4 blob 内层两族是否 dwRoomMessage 位流:
   0x18族(66条,17B) 首5位=00011 -> 疑似位流
   0x02族(195条) 首5位=00000 -> 非位流?
   用 MSB-first 位读器解码, 看 tag 序列是否落在 12 标签词表内。
"""
import json, struct, collections
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

class BR:
    def __init__(self,b): self.b=b; self.pos=0; self.n=len(b)*8
    def bits(self,k):
        v=0
        for _ in range(k):
            if self.pos>=self.n: raise EOFError
            byte=self.b[self.pos>>3]; bit=(byte>>(7-(self.pos&7)))&1
            v=(v<<1)|bit; self.pos+=1
        return v

# 位流标签->位宽 (0x15/0x10/0x13 变长特殊)
WIDTH={0x01:1,0x02:8,0x03:8,0x05:16,0x06:16,0x07:32,0x08:32,0x0a:64,0x0d:32}

def try_decode(inner, maxfields=200):
    br=BR(inner); seq=[]; ok=True
    try:
        while br.pos < br.n-7:  # 至少够5位
            tag=br.bits(5)
            seq.append(tag)
            if tag in WIDTH:
                br.bits(WIDTH[tag])
            elif tag==0x15:
                # 位宽随行: 需要下一个32位立即数 -> 这里无法解, 中止
                seq.append('0x15?'); break
            elif tag==0x10:
                # 变长串: 读8位直到0
                while True:
                    c=br.bits(8)
                    if c==0: break
            elif tag==0x13:
                sub=br.bits(5)
                if sub!=0x08: ok=False;break
                ln=br.bits(32); br.bits(ln*8)
            else:
                ok=False; break
            if len(seq)>maxfields: break
    except EOFError:
        pass
    return seq, ok, br.pos

for b0,label in [(0x18,"0x18族(ready)"),(0x02,"0x02族(room)")]:
    samples=[]
    for r in recs:
        if r.get("svc")==11 and r.get("task")==4:
            for d in blobs(bytes.fromhex(r["payload"])):
                if len(d)>=4 and struct.unpack_from("<I",d,0)[0]==len(d)-4:
                    inner=d[4:]
                    if inner and inner[0]==b0:
                        samples.append(inner)
    print("=== %s : %d 样本 ==="%(label,len(samples)))
    # 前3条完整解码
    for x in samples[:3]:
        seq,ok,pos=try_decode(x)
        print("  len=%dB bits=%d  decoded_bits=%d ok=%s"%(len(x),len(x)*8,pos,ok))
        print("     tags:",seq[:40])
    # 统计首13位类型号
    types=collections.Counter()
    for x in samples:
        br=BR(x)
        try:
            t=br.bits(5); typ=br.bits(8)
            types[(t,typ)]+=1
        except EOFError: pass
    print("  首5位/8位 (tag,type):",dict(types))
    print()
