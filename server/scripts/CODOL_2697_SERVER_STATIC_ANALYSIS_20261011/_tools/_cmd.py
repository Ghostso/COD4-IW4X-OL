import json,io,sys
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
base=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data"
def load(n):
    d=json.load(open(base+"\\"+n,encoding="utf-8")); m={}
    for s in d["symbols"]: m.setdefault(s["name"],s)
    return m
new=load("syms_NEW.json"); old=load("syms_OLD.json"); c13=load("syms_1113.json")
import re
for pat in ["ServerCommand","SendServerCommand","ReliableCommand","TranslateCommand","ProfileCommand","LinkTagCommand"]:
    print("###",pat)
    for k,v in sorted(new.items(),key=lambda x:x[1]["rva"]):
        if pat.lower() in k.lower():
            o=old.get(k); c=c13.get(k)
            print("   NEW %-45s %#010x   OLD=%s  1113=%s"%(k,v["rva"], ("%#x"%o["rva"]) if o else "-", ("%#x"%c["rva"]) if c else "-"))
    print()
