import csv
p=r"D:\BaiduNetdiskDownload\使命召唤OL\XVAL-02_IMAGE_INTEGRITY_AND_REGISTER_AUDIT\XVAL02_QUESTION_REGISTER_MIGRATION.csv"
rows=list(csv.DictReader(open(p,encoding="utf-8-sig")))
tw=sum(float(r["XVAL02_Weight"]) for r in rows)
ts=sum(float(r["XVAL02_Weighted"]) for r in rows)
print("N=%d total_weight=%s total_score=%.4f rate=%.4f%%"%(len(rows),tw,ts,100*ts/tw))
from collections import defaultdict
d=defaultdict(lambda:[0,0.0])
for r in rows:
    imp=r["Hist_Impact"]
    w=float(r["XVAL02_Weight"]); s=float(r["XVAL02_Weighted"])
    d[imp][0]+=w; d[imp][1]+=s
for k in sorted(d): print(k,d[k], "%.4f%%"%(100*d[k][1]/d[k][0]))
print("I4 total",sum(float(r["XVAL02_Weight"]) for r in rows if r["Hist_Impact"]=="I4"),"score",sum(float(r["XVAL02_Weighted"]) for r in rows if r["Hist_Impact"]=="I4"))
print("I4 rate",100*sum(float(r["XVAL02_Weighted"]) for r in rows if r["Hist_Impact"]=="I4")/sum(float(r["XVAL02_Weight"]) for r in rows if r["Hist_Impact"]=="I4"))
