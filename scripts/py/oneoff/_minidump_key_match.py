import json,glob,os
want_ts=0x6096930a; want_size=0xe659000
found=[]
for jp in glob.glob('_*scan.json'):
    try: data=json.load(open(jp,encoding='utf-8'))
    except Exception as e:
        print('ERR',jp,e); continue
    for r in data:
        for m in r.get('modules') or []:
            if m.get('timestamp')==want_ts or m.get('size')==want_size:
                found.append((jp,r['path'],m))
print('DUMP_FILES_INDEXED',sum(len(json.load(open(jp,encoding='utf-8'))) for jp in glob.glob('_*scan.json')))
for jp,dump,m in found:
    print('CAND',jp,'dump=',dump,'base=0x%X size=0x%X ts=0x%08X name=%s'%(m['base'],m['size'],m['timestamp'],m.get('name')))
print('MATCHES',len(found))
