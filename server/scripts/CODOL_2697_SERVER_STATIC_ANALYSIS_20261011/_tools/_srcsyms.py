import json,io,sys,re
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
base=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data"
def load(n):
    d=json.load(open(base+"\\"+n,encoding="utf-8"))
    return d["symbols"]
new=load("syms_NEW.json")
src=set()
for s in new:
    n=s["name"]
    if n.endswith(".c") or n.endswith(".cc") or n.endswith(".cpp"):
        src.add(n)
print("NEW source-file symbols:",len(src))
for n in sorted(src):
    print("   ",n)
