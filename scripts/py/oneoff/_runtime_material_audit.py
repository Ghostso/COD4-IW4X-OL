import os, re, sys, struct, subprocess, hashlib, json, math
from datetime import datetime
root=os.path.abspath(r'D:\BaiduNetdiskDownload\使命召唤OL')

def walk_files(base, lower_suffixes=None, name_pred=None, skip_tvm=True):
    out=[]
    for dp,dn,fn in os.walk(base):
        if skip_tvm:
            dn[:]=[d for d in dn if d.lower() not in ('tvm0',)]
        for n in fn:
            if skip_tvm and n.lower().endswith('.tvm0'):
                continue
            p=os.path.join(dp,n)
            if lower_suffixes is not None and not n.lower().endswith(lower_suffixes):
                continue
            if name_pred is not None and not name_pred(n):
                continue
            try: st=os.stat(p)
            except OSError: continue
            out.append((p,st.st_size,st.st_mtime))
    return out

print('=== PROCESSES ===')
try:
    txt=subprocess.check_output(['tasklist','/FO','CSV','/NH'],text=True,errors='replace')
    rows=[]
    for line in txt.splitlines():
        parts=[x.strip('"') for x in line.split('","')]
        if parts:
            rows.append(parts)
    hits=[r for r in rows if any(re.search(r'codoMP|shipRetail|call.?of.?duty|iw4|codol|使命召唤',x,re.I) for x in r)]
    print('MATCHES',json.dumps(hits,ensure_ascii=False))
    print('TOTAL_PROCESS_ROWS',len(rows))
except Exception as e:
    print('PROCESS_ERROR',repr(e))

print('\n=== WORKSPACE PDBs (excluding .tvm0) ===')
pdbs=walk_files(root,lower_suffixes=('.pdb',))
print('COUNT',len(pdbs))
for p,s,t in pdbs: print(s,datetime.fromtimestamp(t).isoformat(),p)

print('\n=== WORKSPACE DUMP-LIKE FILES (excluding .tvm0) ===')
dump_suffixes=('.dmp','.mdmp','.core','.mem','.vmem','.dump','.minidump','.dat')
cands=walk_files(root,lower_suffixes=dump_suffixes,skip_tvm=True)
filtered=[]
for p,s,t in cands:
    n=os.path.basename(p).lower()
    if any(k in n for k in ('dump','crash','mini','memory','gbdump')) or p.lower().endswith(('.dmp','.mdmp','.core','.mem','.vmem','.dump','.minidump')):
        filtered.append((p,s,t))
print('COUNT',len(filtered))
for p,s,t in sorted(filtered,key=lambda x:x[1],reverse=True):
    try:
        with open(p,'rb') as f: head=f.read(32)
        hx=head.hex()
        sig=head[:4]
    except Exception as e:
        hx=''; sig=repr(e).encode()
    print(s,datetime.fromtimestamp(t).isoformat(),sig,hx,p)

print('\n=== TARGET PE MATCH KEYS ===')
exe=os.path.join(root,'COD OL','codoMP_client_shipRetail.exe')
print('EXE',exe)
try:
    data=open(exe,'rb').read()
    print('SIZE',len(data))
    print('SHA256',hashlib.sha256(data).hexdigest())
    pe=struct.unpack_from('<I',data,0x3c)[0]
    print('PE_OFFSET',hex(pe),'SIG',data[pe:pe+4].hex())
    coff=pe+4
    machine,nsec,ts,ptr_sym,n_sym,opt_size,chars=struct.unpack_from('<HHIIIHH',data,coff)
    opt=coff+20
    magic=struct.unpack_from('<H',data,opt)[0]
    is64=magic==0x20b
    print('MACHINE',hex(machine),'NSECTIONS',nsec,'TIMESTAMP',hex(ts),ts)
    if is64:
        image_base=struct.unpack_from('<Q',data,opt+24)[0]
        size_image=struct.unpack_from('<I',data,opt+56)[0]
        entry=struct.unpack_from('<I',data,opt+16)[0]
        dd=opt+112
    else:
        image_base=struct.unpack_from('<I',data,opt+28)[0]
        size_image=struct.unpack_from('<I',data,opt+56)[0]
        entry=struct.unpack_from('<I',data,opt+16)[0]
        dd=opt+96
    print('IMAGE_BASE',hex(image_base),'SIZE_OF_IMAGE',hex(size_image),size_image,'ENTRY_RVA',hex(entry),'VA',hex(image_base+entry))
    ndir=struct.unpack_from('<I',data,opt+(108 if is64 else 92))[0]
    print('NUMBER_OF_RVA_AND_SIZES',ndir)
    for i in range(min(ndir,16)):
        a,b=struct.unpack_from('<II',data,dd+i*8)
        print('DIR[%d] RVA=0x%08X SIZE=0x%X'%(i,a,b))
    # locate debug data dir and CodeView
    dbg_rva,dbg_size=struct.unpack_from('<II',data,dd+6*8)
    print('DEBUG_DIR',hex(dbg_rva),hex(dbg_size))
    if dbg_rva and dbg_size and dbg_rva+dbg_size<=len(data):
        off=dbg_rva
        for i in range(dbg_size//28):
            e=struct.unpack_from('<IIHHIIII',data,off+i*28)
            if e[6]==2:
                raw_off=e[5]
                rec=data[raw_off:raw_off+e[4]]
                if rec[:4]==b'RSDS' and len(rec)>=24:
                    guid=rec[4:20].hex().upper(); age=struct.unpack_from('<I',rec,20)[0]
                    path=rec[24:].split(b'\0',1)[0].decode('utf-8','replace')
                    print('CODEVIEW_RSDS OFF',hex(raw_off),'GUID',guid,'AGE',age,'PATH',path)
    print('RAW_SIZE',len(data),'EOF',hex(len(data)))
except Exception as e:
    print('PE_ERROR',repr(e))

print('\n=== DEDICATED DUMP DIR ===')
d=os.path.join(root,'COD OL','tqm','dump')
if os.path.isdir(d):
    for n in sorted(os.listdir(d)):
        p=os.path.join(d,n)
        if os.path.isfile(p):
            st=os.stat(p)
            with open(p,'rb') as f: h=f.read(16)
            print(st.st_size,datetime.fromtimestamp(st.st_mtime).isoformat(),h.hex(),p)
else:
    print('MISSING',d)
