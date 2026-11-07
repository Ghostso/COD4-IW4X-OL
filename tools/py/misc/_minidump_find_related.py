import json, os, re
with open('_minidump_scan.json','r',encoding='utf-8') as f: data=json.load(f)
kw=re.compile(r'codo|call[_ -]?of[_ -]?duty|iw4|codol|shipretail|client_ship|call_to_arms',re.I)
for r in data:
    hits=[m for m in r.get('modules',[]) if kw.search(m.get('name') or '')]
    if hits:
        print('\nDUMP',r['size'],r['path'])
        for m in hits: print('  HIT 0x%X 0x%X %s' % (m['base'],m['size'],m['name']))
    mods=r.get('modules') or []
    if mods:
        main=max(mods,key=lambda m:m['size'])
        print('MAIN',os.path.basename(r['path']),'0x%X 0x%X %s' % (main['base'],main['size'],main['name']))
