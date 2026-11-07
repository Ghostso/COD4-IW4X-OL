#!/usr/bin/env python3
"""完整 mmstart 明文行 + 统计每个数字 dvar 的取值分布; 并看 2500/2486/2489/2574/3265 各取值。"""
import json, re, collections
CORPUS=r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
recs=json.load(open(CORPUS,"r",encoding="utf-8"))
if isinstance(recs,dict): recs=recs.get("records") or recs.get("data") or list(recs.values())

# 抓完整的 mmstart 段 (从 'mmstart' 到下一个 '\x00' 或结尾)
samples=[]
valmap=collections.defaultdict(collections.Counter)
for r in recs:
    if r.get("svc")==6 and r.get("task")==14:
        p=bytes.fromhex(r["payload"])
        txt=p.decode("latin1",errors="replace")
        m=re.search(r"mmstart[^\x00]*", txt)
        if m:
            line=m.group(0)
            samples.append(line)
            # 抽 "NUM VAL;" 对
            for mm in re.finditer(r"(\d+)\s+(-?\d+)", line):
                k=mm.group(1)
                if k in ("2486","2489","2574","2500","3265"):
                    valmap[k][mm.group(2)]+=1

print("=== 一条完整 mmstart (最长的) ===")
longest=max(samples,key=len)
print(longest[:600])
print("\n长度:",len(longest),"条数:",len(samples))

print("\n=== 各数字 dvar 的取值分布 ===")
for k in ["2486","2489","2574","2500","3265"]:
    print("  %s -> %s"%(k, dict(valmap[k].most_common(12))))

# 找 mmstart 里所有 "NUM VAL" 形式, 看是不是都是数字名 dvar
print("\n=== 一条 mmstart 里所有 (name value) 对 ===")
line=longest
pairs=re.findall(r"([A-Za-z_][\w/]*|\d+)\s+(-?[\w.]+)", line)
print(pairs[:40])
