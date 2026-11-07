#!/usr/bin/env python3
"""8/3 档案上传: paper09 说 blob 是 zlib(78 01). 验证并解压, 看上传内容结构.
   8/3 结构(104卷): u32×4 + blob(761~1262) + i32×125; u32#4↔blob.
   这里: 取 blob, 试 zlib 解压.
"""
import json, struct, zlib, collections
CORPUS=r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
recs=json.load(open(CORPUS,"r",encoding="utf-8"))
if isinstance(recs,dict): recs=recs.get("records") or recs.get("data") or list(recs.values())
ps=[bytes.fromhex(r["payload"]) for r in recs if r.get("svc")==8 and r.get("task")==3]
print("8/3 条数:",len(ps))
# 全 payload 里找 zlib 头
ok=0;fail=0;dec_lens=collections.Counter()
for p in ps:
    idx=-1
    for sig in (b"\x78\x01",b"\x78\x9c",b"\x78\xda",b"\x78\x5e"):
        j=p.find(sig)
        if j>=0: idx=j;break
    if idx<0: fail+=1;continue
    try:
        dec=zlib.decompress(p[idx:])
        ok+=1; dec_lens[len(dec)]+=1
    except Exception:
        # 也许不是纯 zlib, 试 raw deflate
        try:
            do=zlib.decompressobj(-15); dec=do.decompress(p[idx+2:])
            ok+=1; dec_lens[len(dec)]+=1
        except Exception:
            fail+=1
print("zlib 解压 成功=%d 失败=%d"%(ok,fail))
if dec_lens:
    print("解压后长度分布:",dict(dec_lens.most_common(8)))
# 取第一条完整样本看头部
for p in ps:
    print("\npayload len=%d 头部48B=%s"%(len(p),p[:48].hex()))
    idx=p.find(b"\x78\x01")
    if idx<0:
        for sig in (b"\x78\x9c",b"\x78\xda"):
            idx=p.find(sig)
            if idx>=0: break
    if idx>=0:
        try:
            dec=zlib.decompress(p[idx:])
            print("  zlib@%d 解出 %dB, 前64: %s"%(idx,len(dec),dec[:64].hex()))
            print("  ascii: %r"%dec[:80])
        except Exception as e:
            print("  解压异常:",e)
    break
