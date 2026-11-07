from collections import Counter
p=r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\coop_train_zone.bin'; d=open(p,'rb').read()
s=0x23f980; e=0x23fbd0
for step in [12,14,16,20,24,28,32,36,40,44,56,68]:
 c=Counter(d[o:o+step] for o in range(s,e-step+1,step))
 print(step,[(b.hex(),n) for b,n in c.most_common(5)])
for st in range(s,s+80):
 seq=d[st:e]
 for period in range(8,80):
  n=min(20,len(seq)//period)
  if n>3 and all(seq[i*period:(i+1)*period]==seq[:period] for i in range(n)):
   print('period',period,'start',hex(st),'first',seq[:period].hex()); break
