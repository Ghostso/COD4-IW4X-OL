from pathlib import Path
root=Path(r'D:\BaiduNetdiskDownload\使命召唤OL')
p=root/'run_codol_001'/'runs'/'PHASE7_STATIC_20261023'/'STATIC_ANALYSIS_MANIFEST.json'
print(p, p.exists())
for x in (root/'run_codol_001'/'runs').glob('**/STATIC_ANALYSIS_MANIFEST.json'): print('found',x)
