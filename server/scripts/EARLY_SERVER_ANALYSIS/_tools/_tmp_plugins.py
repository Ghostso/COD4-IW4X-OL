import json
d=json.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\01_ASSET_MAP\_pe_detail.json",encoding="utf-8"))
for k in d:
    kn=k.replace("\\","/")
    if "/plugins/" in kn or kn.endswith("patcher/Kernel33.dll"):
        r=d[k]
        print("== ",k, "| size",r["size"])
        print("   exports:",r.get("exports"))
        print("   version:",r.get("version"))
        print("   imports:", {dll:len(f) for dll,f in r.get("imports",{}).items()})
