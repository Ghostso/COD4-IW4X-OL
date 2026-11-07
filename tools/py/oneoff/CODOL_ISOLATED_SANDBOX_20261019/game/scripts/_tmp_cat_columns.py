import csv
from collections import defaultdict
p=r'scripts/_out/high_reuse_slot_final_refs.csv'
d=defaultdict(list)
for r in csv.DictReader(open(p,encoding='utf-8')):
    d[r['slot_va']].append(r)
for s,rs in d.items():
    print('\n',s,len(rs))
    for r in rs:
        print(r['ref_rva'],r['boundary_status'],r['boundary_confidence'],r['function_root'],r['candidate_linear_extent'],r['candidate_kind'])
