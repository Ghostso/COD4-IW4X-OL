# -*- coding: utf-8 -*-
"""
slot_table_extract.py -- READ ONLY.

Takes the FF15/FF25 operands, decodes them as ABSOLUTE VA (ImageBase 0x00400000),
and asks the four upgrade questions:
   (1) contiguous slot table?
   (2) multiple callers sharing a slot?
   (3) slots hold function/function pointers?
   (4) consistent with the call pattern?

Also computes exact band counts to reconcile earlier 980 / 507 figures.
"""
import sys, struct, collections

def u16(b,o): return struct.unpack_from('<H',b,o)[0]
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def fmt(i): return '0x%08X' % i

def parse_pe(path):
    d=open(path,'rb').read(); pe={'data':d,'file':path,'size':len(d)}
    e=u32(d,0x3C); coff=e+4
    nsec=u16(d,coff+2); optsz=u16(d,coff+16)
    opt=coff+20; magic=u16(d,opt)
    pe['magic']=magic
    if magic==0x10B:
        pe['ib']=u32(d,opt+28); pe['soi']=u32(d,opt+56); pe['entry']=u32(d,opt+16)
        ddoff=opt+96
    else:
        pe['ib']=struct.unpack_from('<Q',d,opt+24)[0]; pe['soi']=u32(d,opt+56)
        pe['entry']=u32(d,opt+16); ddoff=opt+112
    ndd=u32(d,opt+(92 if magic==0x10B else 108)); pe['ndd']=ndd
    pe['dirs']=[(i,u32(d,ddoff+i*8),u32(d,ddoff+i*8+4)) for i in range(min(ndd,16))]
    so=opt+optsz; secs=[]
    for i in range(nsec):
        o=so+i*40
        secs.append({'i':i,'name':d[o:o+8].rstrip(b'\0').decode('latin1'),
                     'vsize':u32(d,o+8),'va':u32(d,o+12),'rawsz':u32(d,o+16),
                     'praw':u32(d,o+20),'chars':u32(d,o+36)})
    pe['secs']=secs; return pe

def sec_of(pe,rva):
    for s in pe['secs']:
        if s['va']<=rva<s['va']+max(s['vsize'],s['rawsz']): return s
    return None
def r2o(pe,rva):
    s=sec_of(pe,rva)
    if not s: return None
    dd=rva-s['va']
    return s['praw']+dd if dd<s['rawsz'] else None

def main():
    pe=parse_pe(sys.argv[1]); d=pe['data']; ib=pe['ib']
    print('FILE %s  ImageBase=%s SizeOfImage=%s Entry=%s'%(pe['file'],fmt(ib),fmt(pe['soi']),fmt(pe['entry'])))

    pos=[]
    for i in range(len(d)-6):
        if d[i]==0xFF and d[i+1] in (0x15,0x25): pos.append(i)
    n15=sum(1 for p in pos if d[p+1]==0x15)
    n25=sum(1 for p in pos if d[p+1]==0x25)
    print('\n[CENSUS] FF15=%d  FF25=%d  total=%d'%(n15,n25,len(pos)))
    print('  (earlier working figure was FF15=980 -- see reconciliation below)')

    # ---- band reconciliation ----
    bands={'0x00400000-0x00FFFFFF':(0x00400000,0x01000000),
           '0x00C00000-0x00FFFFFF':(0x00C00000,0x01000000),
           '0x00000000-0x00FFFFFF':(0x00000000,0x01000000)}
    for nm,(lo,hi) in bands.items():
        c15=sum(1 for p in pos if d[p+1]==0x15 and lo<=u32(d,p+2)<hi)
        c25=sum(1 for p in pos if d[p+1]==0x25 and lo<=u32(d,p+2)<hi)
        print('  operand in %s : FF15=%d FF25=%d total=%d'%(nm,c15,c25,c15+c25))

    # ---- decode operand as absolute VA ----
    recs=[]
    for p in pos:
        op=u32(d,p+2); rva=op-ib
        s=sec_of(pe,rva) if 0<=rva<=0xFFFFFFFF else None
        ins=None
        for sec in pe['secs']:
            if sec['praw']<=p<sec['praw']+sec['rawsz']: ins=sec; break
        recs.append({'off':p,'op':op,'rva':rva,'sec':s,'ins':ins,
                     'off_in_sec':(rva-s['va']) if s else None})
    inimg=[r for r in recs if r['sec']]
    print('\n[DECODE] operand treated as ABSOLUTE VA')
    print('  operands landing in a section : %d / %d'%(len(inimg),len(recs)))
    bysec=collections.Counter(r['sec']['name']+'#%d'%r['sec']['i'] for r in inimg)
    print('  by section                    : %s'%dict(bysec))

    # ---- which section is the "table" ----
    tgtsec=collections.Counter(r['sec']['i'] for r in inimg)
    main_sec=tgtsec.most_common(1)[0][0]
    S=[s for s in pe['secs'] if s['i']==main_sec][0]
    print('\n[MAIN TARGET SECTION] #%d %s va=%s vsize=%s rawsz=%s chars=%08X'%(
        S['i'],S['name'],fmt(S['va']),fmt(S['vsize']),fmt(S['rawsz']),S['chars']))
    print('  callers targeting it: %d'%tgtsec[main_sec])

    # ---- (1) contiguous slot table detection ----
    print('\n[1] CONTIGUOUS SLOT TABLE DETECTION (in target section, DWORD granularity)')
    offs=sorted(set(r['off_in_sec'] for r in inimg if r['sec']['i']==main_sec))
    print('  distinct operand offsets targeted: %d'%len(offs))
    if offs:
        print('  offset range: %s .. %s'%(fmt(offs[0]),fmt(offs[-1])))
    gap=collections.Counter(b-a for a,b in zip(offs,offs[1:]))
    print('  offset gap histogram (top): %s'%gap.most_common(10))

    # scan the raw section bytes for maximal runs of valid code pointers
    print('\n  -- raw scan of target section for maximal runs of valid VA pointers --')
    runs=[]
    n=S['vsize']//4
    cur=None
    for k in range(n):
        rva=S['va']+k*4
        o=r2o(pe,rva)
        ok=False
        if o is not None and o+4<=len(d):
            v=u32(d,o)
            if ib<=v<ib+pe['soi'] and sec_of(pe,v-ib):
                ts=sec_of(pe,v-ib)
                if ts['chars']&0x20000000:  # MEM_EXECUTE -> points at code
                    ok=True
        if ok:
            if cur is None: cur=[k,k]
            else: cur[1]=k
        else:
            if cur is not None:
                if cur[1]-cur[0]+1>=4: runs.append(tuple(cur))
                cur=None
    if cur is not None and cur[1]-cur[0]+1>=4: runs.append(tuple(cur))
    runs.sort(key=lambda r:-(r[1]-r[0]))
    print('  maximal runs (>=4 slots) of code pointers: %d'%len(runs))
    for a,b in runs[:15]:
        print('    %s .. %s  = %d slots (RVAs %s..%s)'%(
            fmt(S['va']+a*4),fmt(S['va']+b*4),b-a+1,fmt(S['va']+a*4),fmt(S['va']+b*4)))
    tot=sum(b-a+1 for a,b in runs)
    print('  total slots inside runs>=4: %d'%tot)

    # ---- (2) callers per slot ----
    print('\n[2] CALLER SHARING')
    cnt=collections.Counter(r['op'] for r in inimg if r['sec'] and r['sec']['i']==main_sec)
    shared=[(v,c) for v,c in cnt.items() if c>1]
    print('  slots in main section with >1 caller: %d of %d distinct'%(len(shared),len(cnt)))
    print('  top shared: %s'%[(fmt(v),c) for v,c in sorted(shared,key=lambda x:-x[1])[:10]])

    # ---- (3) slots hold code pointers? ----
    print('\n[3] SLOT CONTENT CLASSIFICATION (target = main section)')
    cls=collections.Counter()
    for r in inimg:
        if not r['sec'] or r['sec']['i']!=main_sec: continue
        o=r2o(pe,r['rva'])
        if o is None or o+4>len(d): cls['no-file-backing']+=1; continue
        v=u32(d,o); tsec=sec_of(pe,v-ib) if ib<=v<ib+pe['soi'] else None
        if tsec and (tsec['chars']&0x20000000): cls['code pointer (MEM_EXECUTE)']+=1
        elif tsec: cls['pointer to non-exec section']+=1
        elif v==0: cls['NULL']+=1
        else: cls['not a pointer']+=1
    for k,v in cls.most_common(): print('   %-32s %d'%(k,v))

    # ---- (4) does file->RVA mapping reproduce the call encoding? ----
    print('\n[4] ENCODING SANITY: is FF15 <VA> the actual instruction form?')
    print('  sample instructions (file off, section, RVA, operand, target RVA, target section):')
    for r in recs[:6]:
        print('   off=%-8s ins=%-6s rva=%-10s op=%s -> rva=%-10s %s'%(
            hex(r['off']),r['ins']['name'] if r['ins'] else '-',
            fmt(r['off']-r['ins']['praw']+r['ins']['va']) if r['ins'] else '-',
            fmt(r['op']),fmt(r['rva']),
            ('%s#%d+0x%X'%(r['sec']['name'],r['sec']['i'],r['off_in_sec'])) if r['sec'] else 'OUT'))

    # ---- entry point decode ----
    print('\n[ENTRY POINT]')
    eo=r2o(pe,pe['entry'])
    if eo:
        print('  entry RVA %s file off 0x%X bytes=%s'%(fmt(pe['entry']),eo,d[eo:eo+16].hex()))
        if d[eo]==0xFF and d[eo+1] in (0x15,0x25):
            op=u32(d,eo+2); rva=op-ib; s=sec_of(pe,rva)
            print('  entry is FF%02X op=%s -> rva %s %s (aligned=%s)'%(
                d[eo+1],fmt(op),fmt(rva),
                '%s#%d+0x%X'%(s['name'],s['i'],rva-s['va']) if s else 'OUT',
                'YES' if op%4==0 else 'NO (operand not 4-aligned)'))

    # ---- IAT dir cross check ----
    print('\n[DIR CROSS-CHECK]')
    for i,nm in ((1,'IMPORT'),(12,'IAT'),(5,'BASERELOC')):
        ddi,dr,dz=[x for x in pe['dirs'] if x[0]==i][0]
        st='ABSENT' if not (dr or dz) else 'PRESENT'
        n=0
        if dr:
            n=sum(1 for r in recs if dr<=r['rva']<dr+dz)
        print('  dir[%2d] %-9s rva=%s size=0x%X  %s   operands inside=%d'%(
            i,nm,fmt(dr),dz,st,n))

    # ---- where do the referenced slots sit, relative to the big pointer runs ----
    print('\n[SLOT POSITION] 232 referenced slots in main section, sorted:')
    seq=sorted(set(r['off_in_sec'] for r in inimg if r['sec'] and r['sec']['i']==main_sec))
    print('  %s'%' '.join('%X'%o for o in seq))

if __name__=='__main__': main()
