import json,io,sys,re
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
base=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data"
def load(n):
    d=json.load(open(base+"\\"+n,encoding="utf-8"))
    m={}
    for s in d["symbols"]:
        m.setdefault(s["name"],s)
    return m
new=load("syms_NEW.json"); old=load("syms_OLD.json"); c13=load("syms_1113.json")
pat=re.compile(r"2697",re.I)
rows=[(k,v) for k,v in new.items() if pat.search(k)]
print("count 2697-named NEW syms:",len(rows))
for k,v in sorted(rows,key=lambda x:x[1].get("rva",0)):
    print("  %-50s rva=%#010x va=%#010x sec=%s"%(k,v["rva"],v["va"],v["section"]))
