import json,re
p=r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\coop_train_collision_approx.json'
j=json.load(open(p,encoding='utf-8'))
print('clips',len(j['clips']))
for i,c in enumerate(j['clips']): print(i,c)
