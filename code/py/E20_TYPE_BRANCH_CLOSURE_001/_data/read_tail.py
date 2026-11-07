from pathlib import Path
p=Path(r"D:\BaiduNetdiskDownload\使命召唤OL\E20_TYPE_BRANCH_CLOSURE_001\_data\out_6a9920_full.txt")
print("\n".join(p.read_text(encoding="utf-8").splitlines()[120:260]))
