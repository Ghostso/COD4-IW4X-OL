# -*- coding: utf-8 -*-
"""
FF15/FF25 raw operand -> VA/RVA/section mapping.  READ-ONLY.

v2: section labels carry their INDEX (6 sections share the name ".tp3", so a
    bare name is ambiguous).  Adds two discriminators:
      * is the candidate target backed by file bytes, or virtual-only (built
        at runtime)?
      * does the FF15/FF25 byte pair lie INSIDE a declared data directory
        (i.e. it is directory DATA that happens to look like an instruction)?

Wording discipline: "address-like pointer target".  Nothing is called IAT
unless a header directory says so; those header values are printed verbatim.
"""
import sys, struct
from collections import Counter, defaultdict

def u16(b,o): return struct.unpack_from('<H', b, o)[0]
def u32(b,o): return struct.unpack_from('<I', b, o)[0]

def parse_pe(path):
    d = open(path,'rb').read()
    if d[:2] != b'MZ': raise SystemExit('not MZ')
    e = u32(d,0x3C)
    if d[e:e+4] != b'PE\0\0': raise SystemExit('no PE sig')
    c = e+4
    machine=u16(d,c); nsec=u16(d,c+2); tstamp=u32(d,c+4); optsz=u16(d,c+16)
    opt=c+20; magic=u16(d,opt)
    if magic==0x10b:
        ib=u32(d,opt+28); salign=u32(d,opt+32); falign=u32(d,opt+36)
        sizeofimage=u32(d,opt+56); nddir=u32(d,opt+92); ddoff=opt+96; pe32=True
    elif magic==0x20b:
        ib=struct.unpack_from('<Q',d,opt+24)[0]; salign=u32(d,opt+32); falign=u32(d,opt+36)
        sizeofimage=u32(d,opt+56); nddir=u32(d,opt+108); ddoff=opt+112; pe32=False
    else: raise SystemExit('bad magic')
    dirs=[(u32(d,ddoff+i*8), u32(d,ddoff+i*8+4)) for i in range(min(nddir,16))]
    secs=[]; so=opt+optsz
    for i in range(nsec):
        p=so+i*40
        secs.append(dict(name=d[p:p+8].rstrip(b'\0').decode('latin1'), idx=i,
                         vsize=u32(d,p+8), va=u32(d,p+12), rawsize=u32(d,p+16),
                         raw=u32(d,p+20), chars=u32(d,p+36)))
    return dict(data=d, path=path, nsec=nsec, magic=magic, imagebase=ib,
                salign=salign, falign=falign, sizeofimage=sizeofimage,
                dirs=dirs, secs=secs, machine=machine, tstamp=tstamp, pe32=pe32)

def sec_at(pe, rva):
    """section containing rva, by VIRTUAL size (covers unbacked tail)"""
    for s in pe['secs']:
        if s['va'] <= rva < s['va'] + max(s['vsize'], s['rawsize']):
            return s
    return None

def lbl(s):
    return '[%d]%s@0x%08X' % (s['idx'], s['name'], s['va']) if s else '<none>'

def backed(pe, s, rva):
    """True if this rva has real bytes in the file"""
    if not s: return False
    off = rva - s['va']
    return off < s['rawsize']

def off_of_rva(pe, rva):
    s = sec_at(pe, rva)
    if not s: return None
    d = rva - s['va']
    return s['raw'] + d if d < s['rawsize'] else None

def rva_of_off(pe, off):
    for s in pe['secs']:
        if s['raw'] and s['raw'] <= off < s['raw'] + s['rawsize']:
            return s['va'] + (off - s['raw'])
    if pe['secs'] and off < pe['secs'][0]['raw']: return off
    return None

DN={0:'EXPORT',1:'IMPORT',2:'RESOURCE',3:'EXCEPTION',4:'SECURITY',5:'BASERELOC',
    6:'DEBUG',7:'ARCH',8:'GLOBALPTR',9:'TLS',10:'LOAD_CONFIG',11:'BOUND_IMPORT',
    12:'IAT',13:'DELAY_IMPORT',14:'CLR',15:'RESERVED'}

def main():
    pe = parse_pe(sys.argv[1]); d = pe['data']
    print('='*78)
    print('FILE   : %s  (%.2f MB)' % (pe['path'], len(d)/1048576.0))
    print('MACHINE: 0x%04X  %s  SECTIONS: %d  TIMESTAMP: %u'
          % (pe['machine'], 'PE32' if pe['pe32'] else 'PE32+', pe['nsec'], pe['tstamp']))
    print('ImageBase: 0x%08X   SizeOfImage: 0x%X   SecAlign 0x%X  FileAlign 0x%X'
          % (pe['imagebase'], pe['sizeofimage'], pe['salign'], pe['falign']))
    print()
    print('--- SECTION TABLE (header truth; 6 sections share name ".tp3" -> idx matters) ---')
    print('%-6s %-8s %-12s %-12s %-10s %-10s %-10s' %
          ('idx','name','VA','VA_end','VSize','RawSize','Chars'))
    for s in pe['secs']:
        print('%-6d %-8s 0x%08X 0x%08X 0x%-8X 0x%-8X 0x%08X %s' %
              (s['idx'], s['name'], s['va'], s['va']+s['vsize'], s['vsize'],
               s['rawsize'], s['chars'],
               ','.join(n for n,b in (('R',0x40000000),('W',0x80000000),('X',0x20000000),
                                      ('CODE',0x20),('IDATA',0x40),('UDATA',0x80))
                        if s['chars'] & b)))
    print()
    print('--- DATA DIRECTORIES (REAL header values) ---')
    for i,(va,sz) in enumerate(pe['dirs']):
        s = sec_at(pe, va) if va else None
        b = backed(pe, s, va) if s else None
        extra = ''
        if va and s: extra = '  in %s  %s' % (lbl(s), 'BACKED' if b else 'VIRTUAL-ONLY')
        if not va and not sz: extra = '  <EMPTY>'
        print('  dir[%-2d] %-13s RVA=0x%08X size=0x%-8X%s' % (i, DN.get(i,'?'), va, sz, extra))
    print()
    imp = pe['dirs'][1] if len(pe['dirs'])>1 else (0,0)
    iat = pe['dirs'][12] if len(pe['dirs'])>12 else (0,0)
    rel = pe['dirs'][5] if len(pe['dirs'])>5 else (0,0)
    print('HEADER VERDICT: IMPORT dir[1]=%s  IAT dir[12]=%s  BASERELOC dir[5]=%s'
          % ('RVA 0x%X size 0x%X'%imp if imp[0] else 'ABSENT',
             'RVA 0x%X size 0x%X'%iat if iat[0] else 'ABSENT',
             'RVA 0x%X size 0x%X'%rel if rel[0] else 'ABSENT'))
    if imp[0] and imp[1]==0:
        print('  !! IMPORT directory declared with SIZE 0 -> loader sees no import table.')

    ib = pe['imagebase']
    hits=[]
    for opc,nm in ((b'\xff\x15','FF15'),(b'\xff\x25','FF25')):
        i=d.find(opc)
        while i!=-1:
            if i+6<=len(d): hits.append((i,nm,u32(d,i+2)))
            i=d.find(opc,i+1)
    hits.sort()
    n15=sum(1 for h in hits if h[1]=='FF15'); n25=len(hits)-n15
    print()
    print('='*78)
    print('B) CENSUS   FF15=%d  FF25=%d  total=%d' % (n15,n25,len(hits)))
    same = (ib==0x400000)
    print('  ImageBase=0x%08X -> interpretation A (raw as VA) and B (raw-0x400000) are %s'
          % (ib,'IDENTICAL' if same else 'DISTINCT'))

    # instruction-inside-a-directory filter
    def dir_at(rva):
        for i,(va,sz) in enumerate(pe['dirs']):
            if va and sz and va <= rva < va+sz: return DN.get(i,str(i))
        return None

    land=Counter(); land_backed=Counter(); land_unbacked=Counter()
    outside=0; in_dir=Counter(); rows=[]
    for off,nm,raw in hits:
        irva=rva_of_off(pe,off)
        dd = dir_at(irva) if irva is not None else None
        if dd: in_dir[dd]+=1
        rva=raw-ib
        s = sec_at(pe,rva) if 0<=rva<pe['sizeofimage'] else None
        if s is None: outside+=1
        else:
            key='[%d]%s'%(s['idx'],s['name']); land[key]+=1
            (land_backed if backed(pe,s,rva) else land_unbacked)[key]+=1
        rows.append((off,nm,raw,irva,s,backed(pe,s,rva) if s else None))
    print()
    print('  --- candidate target landing (by section index) ---')
    print('     %-16s %8s %8s %8s' % ('section','total','fileBKD','VIRTonly'))
    for k,c in land.most_common():
        print('     %-16s %8d %8d %8d' % (k,c,land_backed[k],land_unbacked[k]))
    print('     %-16s %8d' % ('<outside image>',outside))
    if in_dir:
        print()
        print('  --- hits whose INSTRUCTION rva lies inside a declared data dir ---')
        print('     (these bytes are directory DATA, not code)')
        for k,c in in_dir.most_common(): print('     inside dir[%s]  x%d' % (k,c))

    print()
    print('  --- repeat / slot structure ---')
    ctr=Counter(r for _,_,r in hits)
    rep=sorted([(r,c) for r,c in ctr.items() if c>1], key=lambda t:-t[1])
    print('  distinct operands=%d ; appearing >1 time=%d' % (len(ctr),len(rep)))
    for r,c in rep[:20]:
        s=sec_at(pe,r-ib)
        b=backed(pe,s,r-ib) if s else None
        print('     operand 0x%08X x%-4d -> %-18s %s'
              % (r,c,'[%d]%s'%(s['idx'],s['name']) if s else '<outside>',
                 'BACKED' if b else ('VIRTUAL-ONLY' if s else '')))
    if len(rep)>20: print('     ... %d more' % (len(rep)-20))

    tg=sorted(set(r-ib for _,_,r in hits if 0<=r-ib<pe['sizeofimage']))
    st=Counter();
    for a,b in zip(tg,tg[1:]): st[b-a]+=1
    print()
    print('  --- target spacing histogram ---')
    print('     distinct in-image targets=%d' % len(tg))
    for s_,c in st.most_common(8): print('     stride 0x%-5X x%d' % (s_,c))
    runs=[]; run=[tg[0]] if tg else []
    for a,b in zip(tg,tg[1:]):
        if b-a==4: run.append(b)
        else:
            if len(run)>=4: runs.append(run)
            run=[b]
    if len(run)>=4: runs.append(run)
    print('     contiguous 4-byte runs (len>=4): %d' % len(runs))
    for r_ in sorted(runs,key=len,reverse=True)[:10]:
        s=sec_at(pe,r_[0]); b=backed(pe,s,r_[0]) if s else None
        print('        %3d slots  0x%08X..0x%08X  %-18s %s'
              % (len(r_),r_[0],r_[-1],'[%d]%s'%(s['idx'],s['name']) if s else '?',
                 'BACKED' if b else 'VIRTUAL-ONLY'))
    if len(runs)>10: print('        ... %d more runs' % (len(runs)-10))

    print()
    print('  --- probe: DWORD stored AT each candidate target (file view) ---')
    kinds=Counter(); ex=defaultdict(list)
    for off,nm,raw,irva,s,b in rows:
        rva=raw-ib
        if s is None: kinds['target outside image']+=1; continue
        fo=off_of_rva(pe,rva)
        if fo is None or fo+4>len(d):
            kinds['target VIRTUAL-ONLY (no file bytes)']+=1
            if len(ex['v'])<4: ex['v'].append((rva,s['idx']))
            continue
        v=u32(d,fo)
        if v==0: k='target DWORD == 0'
        elif ib<=v<ib+pe['sizeofimage']:
            s2=sec_at(pe,v-ib); k='target DWORD is in-image ptr -> [%s]'%(s2['idx'] if s2 else '?')
        else: k='target DWORD is non-image value'
        kinds[k]+=1
        if len(ex[k])<4: ex[k].append((rva,v))
    for k,c in kinds.most_common():
        print('     %-46s %6d' % (k,c))
        for e_ in ex[k][:3]:
            print('          eg rva=0x%08X %s' % (e_[0], 'sect[%d]'%e_[1] if len(e_)>1 and k.startswith('target VIRTUAL') else 'val=0x%08X'%e_[1]))

    print()
    print('  --- high band 0x00C00000-0x00FFFFFF (two DIFFERENT readings) ---')
    for tag, sel in (('RAW OPERAND  in [0x00C00000,0x00FFFFFF]',
                      [r for r in rows if 0x00C00000 <= r[2] <= 0x00FFFFFF]),
                     ('candidate RVA in [0x00C00000,0x00FFFFFF]',
                      [r for r in rows if 0x00C00000 <= (r[2] - ib) <= 0x00FFFFFF])):
        print('     %-42s count=%d' % (tag, len(sel)))
        hbs = Counter()
        for r in sel:
            s = r[4]
            hbs['[%d]%s %s' % (s['idx'], s['name'], 'BACKED' if r[5] else 'VIRTUAL-ONLY')
                if s else '<out>'] += 1
        for k, c in hbs.most_common(): print('        %-36s %d' % (k, c))

    print()
    print('  --- 0x0E9DC665 sequence ---')
    seq=bytes.fromhex('FF1565C69D0E'); idxs=[]
    i=d.find(seq)
    while i!=-1: idxs.append(i); i=d.find(seq,i+1)
    print('     exact FF 15 65 C6 9D 0E hits = %d at %s' % (len(idxs),['0x%X'%x for x in idxs]))
    for x in idxs:
        ir=rva_of_off(pe,x); dd=dir_at(ir) if ir is not None else None
        s=sec_at(pe,ir) if ir is not None else None
        print('        fileoff=0x%X insnRVA=0x%X %s  INSIDE dir[%s]'
              % (x, ir or 0, lbl(s), dd))
        print('        operand 0x0E9DC665 -> rva 0x%08X  %s'
              % (0x0E9DC665-ib, 'OUTSIDE SizeOfImage (0x%X)'%pe['sizeofimage']
                 if 0x0E9DC665-ib>=pe['sizeofimage'] else 'in image'))
    print('     4-byte 65C69D0E anywhere = %d' % d.count(b'\x65\xC6\x9D\x0E'))

if __name__=='__main__': main()
