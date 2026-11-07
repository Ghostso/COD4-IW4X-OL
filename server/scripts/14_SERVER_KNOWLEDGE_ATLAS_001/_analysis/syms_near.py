import json
d=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data\syms_NEW.json"
j=json.load(open(d,encoding="utf-8"))
# find symbols near RVA 0xA2E50
for s in j["symbols"]:
    r=s.get("rva",0)
    if isinstance(r,int) and 0xA2DD0<=r<=0xA2F60 and s.get("section")==".text":
        print("0x%08X  %s" % (r, s["name"]))