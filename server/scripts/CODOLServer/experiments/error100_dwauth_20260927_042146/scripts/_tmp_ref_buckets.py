import csv, collections
rs=list(csv.DictReader(open(r'scripts/_out/high_reuse_slot_final_refs.csv',encoding='utf-8')))
for s in ('0x00CA8114','0x00CA8194','0x00CA812C','0x00CA819C','0x00CA8164'):
 x=[r for r in rs if r['slot_va']==s]
 buckets=collections.Counter(int(r['ref_rva'],16)>>16 for r in x)
 print(s,'; '.join('%04Xxx:%d'%(k,v) for k,v in sorted(buckets.items())))
