import re
p=r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\coop_train_entities.txt'
s=open(p,encoding='utf-8',errors='replace').read()
for i,block in enumerate(re.findall(r'\{[^{}]*\}',s,re.S)):
 if 'script_brushmodel' in block:
  kv=dict(re.findall(r'"([^"]+)"\s+"([^"]*)"',block))
  print(i,kv)
