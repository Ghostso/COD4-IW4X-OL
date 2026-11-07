import csv
rows=list(csv.DictReader(open('scripts/_out/ca8000_semantic_slots.csv')))
sent=[r for r in rows if r['class']=='SENT']
print('sentinel_slots',len(sent))
for r in sent:
    if int(r['nrefs'])>0:
        print(r['index'],r['slot'],r['value'],'refs',r['nrefs'],'call',r['call'],'mov',r['mov'],'reads',r['reads'])
print('slots_300_345')
for r in rows[300:345]:
    print(','.join([r['index'],r['slot'],r['value'],r['target_rva'],r['class'],r['nrefs'],r['call'],r['mov']]))
