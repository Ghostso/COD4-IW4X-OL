#!/usr/bin/env python3
"""3265 在 playlist(rule) 与 mmstart 的值域对照; 5 个数字 dvar 的值域汇总; 确认 mmstart 是 dvar 赋值语法。"""
import json, re, collections
CORPUS=r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
recs=json.load(open(CORPUS,"r",encoding="utf-8"))
if isinstance(recs,dict): recs=recs.get("records") or recs.get("data") or list(recs.values())

# mmstart 值域
mm=collections.defaultdict(collections.Counter)
mm_like=0
for r in recs:
    if r.get("svc")==6 and r.get("task")==14:
        p=bytes.fromhex(r["payload"]); txt=p.decode("latin1",errors="replace")
        m=re.search(r"mmstart[^\x00]*",txt)
        if m:
            mm_like+=1
            for mm2 in re.finditer(r"\b(2486|2489|2574|2500|3265)\s+(-?\d+)", m.group(0)):
                mm[mm2.group(1)][mm2.group(2)]+=1
print("mmstart 条数:", mm_like)
print("mmstart 值域:")
for k in ["2486","2489","2574","2500","3265"]:
    print("  %s -> %s"%(k,dict(mm[k].most_common())))

# playlist 值域
pl=collections.Counter()
txt=open(r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\playlist_plain.txt","r",encoding="latin1",errors="replace").read()
for m in re.finditer(r"rule\s+3265\s+(\d+)", txt):
    pl[m.group(1)]+=1
print("\nplaylist rule 3265 值域:", dict(pl.most_common()))
print("  交集 (playlist∩mmstart):", sorted(set(pl)&set(mm["3265"])))

# 其它 4 个是否在 playlist
for k in ["2486","2489","2574","2500"]:
    n=len(re.findall(r"\b"+k+r"\b", txt))
    print("  playlist 里 %s 出现: %d"%(k,n))
