import os, struct, glob, json, sys

def u16(b, o):
    return struct.unpack_from('<H', b, o)[0]
def u32(b, o):
    return struct.unpack_from('<I', b, o)[0]
def u64(b, o):
    return struct.unpack_from('<Q', b, o)[0]

def read_rva(f, rva, size, file_size):
    if rva is None or size is None or rva < 0 or size < 0 or rva + size > file_size:
        return None
    f.seek(rva)
    return f.read(size)

def mdmp_string(f, rva, file_size):
    h = read_rva(f, rva, 4, file_size)
    if not h:
        return None
    n = u32(h,0)
    if n > 32768:
        return None
    raw = read_rva(f, rva+4, n, file_size)
    if raw is None:
        return None
    return raw.decode('utf-16-le', 'replace')

def parse(path):
    out = {'path': path, 'size': os.path.getsize(path), 'modules': [], 'error': None,
           'streams': {}, 'timestamp': None, 'flags': None}
    try:
        with open(path, 'rb') as f:
            h = f.read(32)
            if len(h) < 32 or h[:4] != b'MDMP':
                out['error'] = 'not MDMP'
                return out
            nstreams = u32(h,8); dirdir = u32(h,12)
            out['timestamp'] = u32(h,20); out['flags'] = u64(h,24)
            dirents = read_rva(f,dirdir,nstreams*12,out['size'])
            if dirents is None:
                out['error'] = 'bad stream directory'
                return out
            streams = []
            for i in range(nstreams):
                typ, sz, rva = struct.unpack_from('<III',dirents,i*12)
                streams.append((typ,sz,rva))
                out['streams'].setdefault(typ,[]).append((sz,rva))
            mls = next((x for x in streams if x[0] == 4), None)
            if not mls:
                out['error'] = 'no ModuleListStream'
                return out
            _,sz,rva = mls
            data = read_rva(f,rva,min(sz,4),out['size'])
            if data is None or len(data) < 4:
                out['error'] = 'bad module list'
                return out
            nmods = u32(data,0)
            if nmods > 10000 or 4 + nmods*108 > sz:
                out['error'] = f'bad module count {nmods} size {sz}'
                return out
            mods = read_rva(f,rva,4+nmods*108,out['size'])
            if mods is None:
                out['error'] = 'truncated module list'
                return out
            for i in range(nmods):
                o = 4+i*108
                base = u64(mods,o)
                sizeimg = u32(mods,o+8)
                ts = u32(mods,o+16)
                namerva = u32(mods,o+20)
                name = mdmp_string(f, namerva, out['size'])
                out['modules'].append({'base':base,'size':sizeimg,'timestamp':ts,'name':name,'name_rva':namerva})
    except Exception as e:
        out['error'] = repr(e)
    return out

def main():
    roots=[]
    for x in (os.environ.get('TEMP'), os.environ.get('LOCALAPPDATA','') + r'\Temp', os.environ.get('LOCALAPPDATA','') + r'\CrashDumps'):
        if x and os.path.isdir(x) and x not in roots: roots.append(x)
    seen=set(); files=[]
    for root in roots:
        for base,dirs,names in os.walk(root):
            for name in names:
                if name.lower().endswith(('.dmp','.mdmp','.minidump')):
                    p=os.path.join(base,name)
                    k=os.path.normcase(os.path.abspath(p))
                    if k not in seen:
                        seen.add(k); files.append(p)
    files.sort(key=lambda p: os.path.getsize(p), reverse=True)
    matches=[]; summaries=[]
    for idx,p in enumerate(files):
        r=parse(p)
        mods=r['modules']; target=[m for m in mods if (m.get('name') or '').lower().endswith('codomp_client_shipretail.exe')]
        print(f"SCAN {idx+1}/{len(files)} size={r['size']} modules={len(mods)} target={len(target)} err={r['error']} {p}", flush=True)
        if target:
            for m in target:
                print('  TARGET base=0x%016X size=0x%X ts=0x%08X name=%s' % (m['base'],m['size'],m['timestamp'],m['name']), flush=True)
            matches.append(r)
        summaries.append(r)
    with open('_minidump_scan.json','w',encoding='utf-8') as f:
        json.dump(summaries,f,ensure_ascii=False,indent=2)
    print('MATCHED_DUMPS',len(matches))
if __name__=='__main__':
    main()
