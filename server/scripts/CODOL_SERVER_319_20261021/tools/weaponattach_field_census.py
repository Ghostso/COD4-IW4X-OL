# -*- coding: utf-8 -*-
"""Summarise 3.19 type-43 records by source field and attachment usage."""
from pathlib import Path
import json, collections
ROOT=Path(r'D:\BaiduNetdiskDownload\使命召唤OL')
j=json.loads((ROOT/'CODOL_SERVER_319_20261021'/'fixtures'/'common_mp_weaponattach_records_20261023.json').read_text(encoding='utf-8'))
byfield=collections.Counter(); bytype=collections.Counter(); byflags=collections.Counter(); byindex=collections.Counter(); total=0
for a in j['assets']:
    for r in a['records']:
        total+=1; byfield[r['raw_offset']&0xFFFF]+=1; bytype[r['type']]+=1; byflags[r['flags']]+=1; byindex[r['index']]+=1
out={'total_records':total,'by_type':dict(sorted(bytype.items())),'by_index':dict(sorted(byindex.items())),
     'top_fields':[{'offset':o,'count':c} for o,c in byfield.most_common(80)],
     'top_flags':[{'flags':f,'count':c} for f,c in byflags.most_common(40)]}
path=ROOT/'CODOL_SERVER_319_20261021'/'fixtures'/'common_mp_weaponattach_field_census_20261023.json'
path.write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding='utf-8')
print('records',total,'fields',len(byfield),'types',len(bytype),'indices',len(byindex),'wrote',path)
for x in out['top_fields'][:30]: print(hex(x['offset']),x['count'])
