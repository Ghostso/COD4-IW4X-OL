import json,io,sys
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
base=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data"
d=json.load(open(base+r"\pe_meta.json",encoding="utf-8"))
by={}
for e in d: by[e["path"].split("\\")[-3]+"|"+e["sha256"][:8]]=e
new=d[0]; old=d[1]; c13=d[2]
def imp(e):
    s=set()
    for dll,fns in e["imports"].items():
        for f in fns: s.add(dll.lower()+"!"+f)
    return s
ni,oi,ci=imp(new),imp(old),imp(c13)
def show(title,s): 
    print("### "+title+" (%d)"%len(s))
    for x in sorted(s): print("   ",x)
show("NEW-only vs OLD",ni-oi)
show("OLD-only vs NEW",oi-ni)
show("NEW-only vs 1113",ni-ci)
print()
print("NEW export count",len(new["exports"]),"OLD",len(old["exports"]),"1113",len(c13["exports"]))
print("exports identical NEW/OLD:", sorted(new["exports"])==sorted(old["exports"]))
print("exports identical NEW/1113:", sorted(new["exports"])==sorted(c13["exports"]))
