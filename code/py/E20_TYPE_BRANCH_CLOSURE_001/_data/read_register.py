import csv
p=r"D:\BaiduNetdiskDownload\使命召唤OL\XVAL-02_IMAGE_INTEGRITY_AND_REGISTER_AUDIT\XVAL02_QUESTION_REGISTER_MIGRATION.csv"
rows=list(csv.DictReader(open(p,encoding="utf-8-sig")))
print("rows",len(rows))
for r in rows:
    print(r["Stable_ID"],r["XVAL02_State"],r["XVAL02_Weight"],r["XVAL02_Score"],r["XVAL02_Weighted"])
