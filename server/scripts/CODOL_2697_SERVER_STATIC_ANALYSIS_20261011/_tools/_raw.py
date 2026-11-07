import json,io,sys
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
base=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data"
for f in ["syms_NEW.json","syms_OLD.json","syms_1113.json"]:
    d=json.load(open(base+"\\"+f,encoding="utf-8"))
    print(f,"raw n_symbols",d["n_symbols"])
