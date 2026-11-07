from pathlib import Path
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\include\codol_weaponattach_scalar_firingrange.inc')
lines=p.read_text(encoding='utf-8').splitlines()
names=[]
for line in lines:
    line=line.strip()
    if line.startswith('{"'):
        names.append('  "'+line.split('"')[1]+'",')
Path(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\include\codol_weaponattach_names.inc').write_text('\n'.join(names)+'\n',encoding='utf-8')
print('names',len(names))
