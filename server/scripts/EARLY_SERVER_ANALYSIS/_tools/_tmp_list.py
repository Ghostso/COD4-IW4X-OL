import csv
rows=list(csv.DictReader(open(r"D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\01_ASSET_MAP\EARLY_SERVER_01_PE_CATALOG.csv",encoding="utf-8")))
print("total PE:",len(rows))
for r in rows:
    p=r["relpath"]
    if "pyenv" in p.lower() or "pyinstaller" in p.lower() or "python" in p.lower(): continue
    print("%-5s dll=%-5s %9s exp=%4s %s" % (r["arch"], r["is_dll"], r["size"], r["export_count"], p))
