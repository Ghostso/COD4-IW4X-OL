import json
j=json.load(open(r'fixtures\coop_train_clipmap_20261023.json',encoding='utf-8'))
print(j['layout'])
for i,b in enumerate(j['brushes']): print(i,b)
