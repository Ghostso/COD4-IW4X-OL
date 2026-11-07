import json,io,sys,re
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
base=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data"
def load(n):
    d=json.load(open(base+"\\"+n,encoding="utf-8")); m={}
    for s in d["symbols"]: m.setdefault(s["name"],s)
    return m
new=load("syms_NEW.json"); old=load("syms_OLD.json"); c13=load("syms_1113.json")
n2697={k for k in new if re.search("2697",k)}
print("2697-named total NEW:",len(n2697))
print("also in OLD:",len(n2697&set(old)))
print("also in 1113:",len(n2697&set(c13)))
print("absent from both:",len(n2697-set(old)-set(c13)))
