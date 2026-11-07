import json
d=json.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\01_ASSET_MAP\_pe_detail.json",encoding="utf-8"))
for k in d:
    if k.replace("\\","/").endswith("bin/codol_dedrun.exe"):
        r=d[k]
        print("== ",k)
        print("arch",r["arch"],"IB",r["imagebase"],"EP",r["entrypoint_rva"],"ts",r["timestamp"],"linker",r["linker"])
        print("sections:",[ (s["name"],s["vsize"],s["rawsize"]) for s in r["sections"]])
        print("imports:")
        for dll,fns in r["imports"].items():
            print("  ",dll,len(fns))
        print("exports count",r["export_count"])
        print("first 40 exports:",r["exports"][:40])
        print("version",r.get("version"))
