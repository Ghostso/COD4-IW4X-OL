import csv,re,os
p=r'D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\GDP_CMD_MAP.csv'
rows=list(csv.DictReader(open(p,encoding='utf-8')))
cf=[r for r in rows if r['table']=='A' and r['name'].startswith('GDP_CF_')]
cf.sort(key=lambda r:int(r['enum'],16))
print('GDP_CF_ commands:',len(cf))
for r in cf: print('  %s  %s'%(r['enum'],r['name']))
