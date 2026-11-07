import json,io,sys
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
base=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data"
def load(n):
    d=json.load(open(base+"\\"+n,encoding="utf-8")); m={}
    for s in d["symbols"]: m.setdefault(s["name"],s)
    return m
new=load("syms_NEW.json"); old=load("syms_OLD.json"); c13=load("syms_1113.json")
ns,os_,cs=set(new),set(old),set(c13)
print("symbols NEW",len(ns),"OLD",len(os_),"1113",len(cs))
print("NEW-only vs OLD",len(ns-os_))
print("OLD-only vs NEW",len(os_-ns))
print("NEW-only vs 1113",len(ns-cs))
print("(NEW∩OLD) only",len(ns&os_))
# Plugin_ export symbols
pk=[k for k in new if k.startswith("Plugin_")]
print("Plugin_ syms NEW",len(pk))
# 2697-ish NEW-only symbol count
import re
n2697=[k for k in ns-os_ if re.search("2697",k)]
print("2697-named NEW-only-vs-OLD",len(n2697))
