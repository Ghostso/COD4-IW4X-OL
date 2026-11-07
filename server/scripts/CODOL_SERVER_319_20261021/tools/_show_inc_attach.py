from pathlib import Path
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\include\codol_weaponattach_scalar_firingrange.inc')
s=p.read_text(encoding='utf-8')
for line in s.splitlines():
    if '"highcal_base"' in line or '"fmj_base"' in line: print(line)
