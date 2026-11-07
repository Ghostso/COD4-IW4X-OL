import json,io,sys
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
base=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data"
d=json.load(open(base+r"\pe_meta.json",encoding="utf-8"))
names=["NEW","OLD","1113"]
for e,nm in zip(d,names):
    print("===",nm,e["sha256"][:12])
    print("  %-8s %-10s %-10s %-10s %-8s"%("name","VA","VSize","RawSize","Entropy"))
    for s in e["sections"]:
        print("  %-8s %-10s %-10s %-10s %-8s"%(s["name"],s["VA"],s["VSize"],s["RawSize"],s["Entropy"]))
    print()
