import csv
rs=list(csv.DictReader(open(r'scripts/_out/high_reuse_slot_final_refs.csv',encoding='utf-8')))
for s in ('0x00CA8114','0x00CA8194','0x00CA812C','0x00CA819C','0x00CA8164'):
 x=[r for r in rs if r['slot_va']==s]
 print('\n'+s)
 for r in x: print(r['ref_rva'],'PRE',r['pre64'],'POST',r['post64'])
