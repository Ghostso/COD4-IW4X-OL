import csv, collections
rs=list(csv.DictReader(open(r'scripts/_out/high_reuse_slot_final_refs.csv',encoding='utf-8')))
for slot in ('0x00CA8114','0x00CA8194','0x00CA812C','0x00CA819C','0x00CA8164'):
 print('\n===',slot,'===')
 ss=[r for r in rs if r['slot_va']==slot]
 for n in (4,6,8,12,16):
  c=collections.Counter(r['pre64'][-2*n:] for r in ss if len(r['pre64'])>=2*n)
  dup=[(k,v) for k,v in c.items() if v>1]
  print('pre',n,'dup_groups',len(dup),'events',sum(v for _,v in dup))
  for k,v in sorted(dup,key=lambda x:(-x[1],x[0]))[:8]: print(' ',v,k)
 print('post patterns')
 for n in (4,6,8,12,16):
  c=collections.Counter(r['post64'][:2*n] for r in ss if len(r['post64'])>=2*n)
  dup=[(k,v) for k,v in c.items() if v>1]
  print('post',n,'dup_groups',len(dup),'events',sum(v for _,v in dup))
  for k,v in sorted(dup,key=lambda x:(-x[1],x[0]))[:8]: print(' ',v,k)
