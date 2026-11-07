#!/usr/bin/env python3
"""验证 11/4 blob 内层 0x02族 = [头部][dwRoomMessage 位流].
   证据线索: 反复出现的 'ab' 字节 = 10101011, 含大量 10101 = 位流 tag 0x15.
   做法: 对每个内层, 扫 bit offset 0..40, 用 12标签词表解码, 找能"干净吃到末尾"的 offset。
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
inner=[]
for r in recs:
    if r.get("svc")==11 and r.get("task")==4:
        for d in blobs(bytes.fromhex(r["payload"])):
            if len(d)>=4 and struct.unpack_from("<I",d,0)[0]==len(d)-4:
                inner.append(d[4:])

class BR:
    def __init__(self,b,startbit=0): self.b=b; self.pos=startbit; self.n=len(b)*8
    def bits(self,k):
        v=0
        for _ in range(k):
            if self.pos>=self.n: raise EOFError
            byte=self.b[self.pos>>3]; bit=(byte>>(7-(self.pos&7)))&1
            v=(v<<1)|bit; self.pos+=1
        return v
WIDTH={0x01:1,0x02:8,0x03:8,0x05:16,0x06:16,0x07:32,0x08:32,0x0a:64,0x0d:32}
def decode_at(b,off,maxf=400):
    br=BR(b,off); tags=[];
    try:
        while br.pos < br.n:
            if br.n-br.pos < 5: return tags,False,"tail"
            tag=br.bits(5); tags.append(tag)
            if tag in WIDTH: br.bits(WIDTH[tag])
            elif tag==0x15: return tags,False,"hit15"
            elif tag==0x10:
                while True:
                    c=br.bits(8)
                    if c==0: break
            elif tag==0x13:
                if br.bits(5)!=0x08: return tags,False,"blobsub"
                br.bits(br.bits(32)*8)
            else: return tags,False,"badtag%02x"%tag
            if len(tags)>maxf: return tags,False,"maxf"
    except EOFError: return tags,False,"eof"
    return tags,True,"clean"

# 对 0x02族: 每个 offset 统计有多少条能"干净"解(不含0x15中止)
fam02=[x for x in inner if x and x[0]==0x02]
print("0x02族 %d 条; 扫 offset 0..40 位, 统计 clean 数:"%len(fam02))
best=[]
for off in range(0,41):
    clean=0; total_tags=0
    for x in fam02:
        tags,ok,why=decode_at(x,off)
        if ok: clean+=1; total_tags+=len(tags)
    best.append((clean,off,total_tags))
best.sort(reverse=True)
for clean,off,tt in best[:12]:
    print("  offset=%2d clean=%3d/%d 总tag=%d"%(off,clean,len(fam02),tt))

# 打印最佳offset下几个样本的tag序列(含0x15也要看)
print("\n最佳 offset 详情:")
bo=best[0][1]
for x in fam02[:5]:
    tags,ok,why=decode_at(x,bo)
    print("  len=%d off=%d ok=%s why=%s tags[:30]=%s"%(len(x),bo,ok,why,tags[:30]))

# 同样测 0x18族 (应为非位流)
fam18=[x for x in inner if x and x[0]==0x18]
print("\n0x18族 %d 条 扫 offset:"%len(fam18))
for off in range(0,16):
    clean=sum(1 for x in fam18 if decode_at(x,off)[1])
    if clean: print("  offset=%2d clean=%d"%(off,clean))
