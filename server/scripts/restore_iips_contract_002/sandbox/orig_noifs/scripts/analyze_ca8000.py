# -*- coding: utf-8 -*-
"""Read-only structural analysis of the 0xCA8000 indirect target table.

Section identity is always the section index, because the executable contains
multiple sections named .tp3.
"""
import sys, os, struct, collections, math, re, json

U16=lambda b,o: struct.unpack_from('<H',b,o)[0]
U32=lambda b,o: struct.unpack_from('<I',b,o)[0]
I32=lambda b,o: struct.unpack_from('<i',b,o)[0]
def hx(x): return '0x%08X'%x

def parse_pe(path):
    d=open(path,'rb').read()
    if d[:2]!=b'MZ': raise SystemExit('not MZ')
    e=U32(d,0x3c)
    if d[e:e+4]!=b'PE\0\0': raise SystemExit('not PE')
    coff=e+4; nsec=U16(d,coff+2); optsz=U16(d,coff+16)
    opt=coff+20; magic=U16(d,opt)
    if magic==0x10b:
        ib=U32(d,opt+28); soi=U32(d,opt+56); entry=U32(d,opt+16); ddoff=opt+96
    elif magic==0x20b:
        ib=struct.unpack_from('<Q',d,opt+24)[0]; soi=U32(d,opt+56); entry=U32(d,opt+16); ddoff=opt+112
    else: raise SystemExit('bad optional magic')
    ndd=U32(d,opt+(92 if magic==0x10b else 108))
    dirs=[(i,U32(d,ddoff+i*8),U32(d,ddoff+i*8+4)) for i in range(min(ndd,16))]
    secoff=opt+optsz; secs=[]
    for i in range(nsec):
        o=secoff+i*40
        secs.append({'i':i,'name':d[o:o+8].rstrip(b'\0').decode('latin1'),
                     'vsize':U32(d,o+8),'va':U32(d,o+12),'rawsz':U32(d,o+16),
                     'praw':U32(d,o+20),'chars':U32(d,o+36)})
    return {'path':path,'data':d,'size':len(d),'e':e,'nsec':nsec,'magic':magic,
            'ib':ib,'soi':soi,'entry':entry,'dirs':dirs,'secs':secs}

def sec_of(pe,rva):
    for s in pe['secs']:
        if s['va']<=rva<s['va']+max(s['vsize'],s['rawsz']): return s
    return None

def r2o(pe,rva):
    s=sec_of(pe,rva)
    if not s: return None
    x=rva-s['va']
    return s['praw']+x if 0<=x<s['rawsz'] else None

def o2r(pe,off):
    for s in pe['secs']:
        if s['praw']<=off<s['praw']+s['rawsz']: return s['va']+off-s['praw'],s
    return None,None

def fmtsec_by_rva(pe,rva):
    s=sec_of(pe,rva)
    return '%s#%d+0x%X'%(s['name'],s['i'],rva-s['va']) if s else 'OUT'

def entropy(data):
    if not data: return 0.0
    c=collections.Counter(data); n=len(data)
    return -sum((v/n)*math.log(v/n,2) for v in c.values())

def runs_ascii(data,minlen=4):
    out=[]
    for m in re.finditer(rb'[ -~]{%d,}'%minlen,data): out.append((m.start(),m.group().decode('latin1')))
    return out

def all_ff_operands(pe):
    d=pe['data']; out=[]
    for p in range(len(d)-6):
        if d[p]==0xff and d[p+1] in (0x15,0x25):
            r,s=o2r(pe,p); op=U32(d,p+2)
            out.append({'off':p,'rva':r,'sec':s,'opcode':d[p+1],'op':op,
                        'slot_rva':op-pe['ib'],'slot_sec':sec_of(pe,op-pe['ib'])})
    return out

def main():
    if len(sys.argv)<2: raise SystemExit('usage: analyze_ca8000.py <pe>')
    pe=parse_pe(sys.argv[1]); d=pe['data']; ib=pe['ib']
    print('FILE=%s size=0x%X ImageBase=%s SizeOfImage=%s Entry=%s'%(
        os.path.basename(pe['path']),pe['size'],hx(ib),hx(pe['soi']),hx(pe['entry'])))
    print('[SECTIONS]')
    for s in pe['secs']:
        print('  #%d %-8s VA=%s..%s VSize=0x%X RawPtr=%s RawSize=0x%X chars=%08X'%(
            s['i'],s['name'],hx(s['va']),hx(s['va']+s['vsize']),s['vsize'],hx(s['praw']),s['rawsz'],s['chars']))
    print('[DIRS] '+'; '.join('dir[%d]=%s/0x%X'%(i,hx(r) if r else 'ABSENT',z) for i,r,z in pe['dirs'] if i in (1,4,5,12)))
    target_va=0x00ca8000; target_rva=target_va-ib; S=sec_of(pe,target_rva); base_off=r2o(pe,target_rva)
    print('TABLE VA=%s RVA=%s FILEOFF=%s SECTION=%s#%d chars=%08X'%(
        hx(target_va),hx(target_rva),hx(base_off),S['name'],S['i'],S['chars']))

    rows=[]
    for j in range(512):
        va=target_va+j*4; off=r2o(pe,va-ib); raw=U32(d,off) if off is not None and off+4<=len(d) else None
        trva=raw-ib if raw is not None and ib<=raw<ib+pe['soi'] else None
        ts=sec_of(pe,trva) if trva is not None else None
        rows.append({'i':j,'slot_va':va,'slot_rva':va-ib,'slot_off':off,'raw':raw,
                     'in_image':ts is not None,'value_rva':trva,'target_section':ts,
                     'target_off':r2o(pe,trva) if trva is not None else None})
    inimg=[r for r in rows if r['in_image']]
    print('\n[512-DWORD HEADER/TABLE SUMMARY]')
    print('in_image=%d out_of_image=%d unique=%d aligned4=%d low2=%s zero=%d'%(
        len(inimg),512-len(inimg),len(set(r['raw'] for r in inimg)),sum(r['raw']%4==0 for r in inimg),
        dict(sorted(collections.Counter(r['raw']&3 for r in inimg).items())),sum(r['raw']==0 for r in rows)))
    print('in-image section distribution='+str(dict(collections.Counter('#%d %s'%(r['target_section']['i'],r['target_section']['name']) for r in inimg))))
    print('high-byte groups='+str(dict(sorted(collections.Counter('%02X'%(r['raw']>>24) for r in inimg).items()))))
    print('first16='+' '.join('%08X'%r['raw'] for r in rows[:16]))
    print('last16='+' '.join('%08X'%r['raw'] for r in rows[-16:]))

    # complete targeted subsets
    target_lo=0x00a13000; target_hi=0x00a15300
    win=[r for r in inimg if target_lo<=r['raw']<target_hi]
    print('\n[VALUES IN %s..%s)'%(hx(target_lo),hx(target_hi)))
    print('count=%d min=%s max=%s aligned4=%d low2=%s'%(
        len(win),hx(min(r['raw'] for r in win)),hx(max(r['raw'] for r in win)),
        sum(r['raw']%4==0 for r in win),dict(sorted(collections.Counter(r['raw']&3 for r in win).items()))))
    print('index list='+' '.join(str(r['i']) for r in win))
    # index runs
    def runs_by_index(rs):
        out=[]; cur=[]
        for r in rs:
            if not cur or r['i']==cur[-1]['i']+1: cur.append(r)
            else:
                if len(cur)>=2: out.append(cur)
                cur=[r]
        if len(cur)>=2: out.append(cur)
        return out
    print('index-consecutive runs>=2:')
    for x in sorted(runs_by_index(win),key=lambda z:(-len(z),z[0]['i'])):
        print('  idx %d..%d n=%d values %s..%s'%(x[0]['i'],x[-1]['i'],len(x),hx(x[0]['raw']),hx(x[-1]['raw'])))

    # full table grouping by high byte and duplicates
    print('\n[OUT-OF-IMAGE VALUE STRUCTURE]')
    outv=[r for r in rows if not r['in_image']]
    print('out_count=%d zero=%d high-byte counts=%s'%(len(outv),sum(r['raw']==0 for r in outv),
          dict(sorted(collections.Counter('%02X'%(r['raw']>>24) for r in outv).items()))))
    for pref in (0x80,0x81,0x83,0x8b,0x8d,0x90,0xf0,0xf1):
        rs=[r for r in outv if r['raw']>>24==pref]
        if rs:
            print('  prefix %02X n=%d indices=%s values=%s'%(pref,len(rs),
                  ','.join(str(r['i']) for r in rs),' '.join(hx(r['raw']) for r in rs)))

    # exact scan and attributed events
    ev=all_ff_operands(pe)
    refs=collections.defaultdict(list)
    for x in ev:
        if target_rva<=x['slot_rva']<target_rva+0x800 and x['slot_rva']%4==0:
            refs[x['op']].append(x)
    print('\n[FF15/FF25 REFERENCE SET]')
    print('events=%d ff15=%d ff25=%d table_events=%d table_slots=%d'%(
        len(ev),sum(x['opcode']==0x15 for x in ev),sum(x['opcode']==0x25 for x in ev),
        sum(len(v) for v in refs.values()),len(refs)))
    for op,v in sorted(refs.items(),key=lambda kv:(-len(kv[1]),kv[0])):
        j=(op-target_va)//4; r=rows[j]; rc=collections.Counter(('#%d'%x['sec']['i']) if x['sec'] else 'NOFILE' for x in v)
        print('  %s idx=%d raw=%s target=%s refs=%d bysec=%s'%(
            hx(op),j,hx(r['raw']),fmtsec_by_rva(pe,r['value_rva']) if r['value_rva'] is not None else 'OUT',len(v),dict(rc)))
        print('    caller_rvas='+' '.join(hx(x['rva']) for x in sorted(v,key=lambda z:z['rva'] or 0)))

    # Caller validation with Capstone: recover the actual instruction containing each event.
    print('\n[CAPSTONE CALLSITE VALIDATION / OPERAND TYPE]')
    try:
        from capstone import Cs, CS_ARCH_X86, CS_MODE_32
        md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
    except Exception as e:
        md=None; print('  capstone unavailable: %r'%e)
    confirmed=[]; deltas=collections.Counter()
    if md:
        for x in ev:
            if not x['sec'] or not (x['sec']['chars']&0x20000000): continue
            start=x['rva']-64; so=r2o(pe,start)
            if so is None: continue
            code=d[so:so+96+x['sec']['va']-start] if False else d[so:so+96]
            found=None
            for ins in md.disasm(code,ib+start):
                ia=ins.address-ib
                if ia<=x['rva']<ia+ins.size:
                    found=ins; break
            if not found: continue
            mnem=found.mnemonic; ops=found.operands
            memop=any(o.type==3 and o.mem.base==0 and o.mem.index==0 for o in ops)
            line='%s %s'%(mnem,found.op_str)
            rec={'event':x,'ins':found,'line':line,'memop':memop}
            confirmed.append(rec)
            if x['opcode']==0x15: deltas[('FF15',mnem,'mem' if memop else 'other')]+=1
            else: deltas[('FF25',mnem,'mem' if memop else 'other')]+=1
    print('  decoded events=%d of %d; mnemonic/memory classes=%s'%(len(confirmed),len(ev),dict(deltas)))
    # exact pattern classification for all events, independent of disassembly
    classpat=collections.Counter()
    for x in ev:
        off=x['off']; b=d[off:off+6]
        ismem=(len(b)==6 and b[2:6]!=b'\0\0\0\0')
        classpat['FF%02X absolute disp32'%x['opcode']]+=1
    print('  raw encoding classes=%s'%dict(classpat))
    # check whether any event can be an immediate-relative indirect (modrm!=0x15/0x25)
    print('  all scanned FF15/25 are absolute disp32 by encoding convention (bytes FF 15/25 + disp32)')

    # table grouping used by code: identify runs in slot-address and refs
    print('\n[SLOT ORDER AND REFERENCE RUNS]')
    allslots=sorted(refs)
    for a,b in zip(allslots,allslots[1:]):
        if b-a>4 and (b-a)>=0x20:
            print('  reference gap %s -> %s = 0x%X'%(hx(a),hx(b),b-a))

    # target object window analysis
    print('\n[TARGET WINDOW CONTENT]')
    for lo,hi,name in ((target_lo,target_hi,'object-window'),(0x00a13000,0x00a16000,'window-plus')):
        so=r2o(pe,lo-ib); eo=r2o(pe,hi-1-ib)
        if so is None or eo is None:
            sec=sec_of(pe,lo-ib)
            print('  %s VA=%s..%s section=%s#%d NOT RAW-BACKED (initial PE image semantics: zero fill; runtime bytes unknown)'%(name,hx(lo),hx(hi),sec['name'],sec['i']))
            continue
        b=d[so:eo+1]; sec=sec_of(pe,lo-ib)
        print('  %s VA=%s..%s section=%s#%d file=%s..%s bytes=%d entropy=%.4f zero=%d printable=%d'%(
            name,hx(lo),hx(hi),sec['name'],sec['i'],hx(so),hx(eo),len(b),entropy(b),b.count(0),sum(32<=x<127 for x in b)))
        esc=runs_ascii(b,4); print('   ASCII runs>=4: %d'%len(esc))
        for o,s in esc[:30]: print('    +0x%X %r'%(o,s))
        w=[U32(b,k) for k in range(0,len(b)-3,4)]
        print('   aligned dwords: zero=%d in_image=%d strings_ascii4=%d top=%s'%(
            sum(x==0 for x in w),sum(ib<=x<ib+pe['soi'] for x in w),sum(1 for x in w if all(32<=((x>>(8*k))&255)<127 for k in range(4))),
            ', '.join('%s x%d'%(hx(v),n) for v,n in collections.Counter(w).most_common(10))))
    print('\n[TARGET WINDOW FIRST 0x500 ALIGNED DWORD/ASCII]')
    lo=target_lo; so=r2o(pe,lo-ib)
    endoff=r2o(pe,target_hi-1-ib)
    if so is None or endoff is None:
        print('  SKIP: target window is not raw-backed; on-disk bytes unavailable')
    for i in range(0,0 if so is None or endoff is None else min(0x500,endoff-so+1),0x10):
        vals=[U32(d,so+i+k) for k in range(0,16,4)]
        print('  %s  %s  |%s|'%(hx(lo+i),' '.join('%08X'%v for v in vals),
              ''.join(chr(x) if 32<=x<127 else '.' for x in d[so+i:so+i+16])))

    # periodic/stride analysis on object window
    ts=r2o(pe,target_lo-ib); te=r2o(pe,target_hi-1-ib)
    b=d[ts:te+1] if ts is not None and te is not None else b''
    print('\n[TARGET WINDOW PERIODICITY]')
    for stride in range(2,129):
        n=len(b)-stride; eq=sum(b[i]==b[i+stride] for i in range(n))
        if eq/n>0.60: print('  stride=%d repeat=%.4f'%(stride,eq/n))
    # target values as offsets from window base/delta histogram
    vals=sorted(r['raw'] for r in win)
    print('  target value deltas (top): %s'%collections.Counter(b-a for a,b in zip(vals,vals[1:])).most_common(20))
    print('  target low-byte histogram: %s'%collections.Counter(v&0xff for v in vals).most_common(20))

    # resolve nearby in-image words as possible object fields / pointers
    print('\n[TARGET WINDOW TARGET-ADDRESS CROSS REFERENCES]')
    # for each referenced target value, inspect 16 bytes around it
    for r in win:
        if r['target_off'] is None: continue
        # print only first/last and selected interesting unaligned families
        if r['i'] in (53,54,55,218,219,300,386,417,418,464,465,475,511):
            o=r['target_off']; a=d[o:o+0x20]
            print('  idx=%d slot=%s -> %s bytes=%s words=%s'%(
                r['i'],hx(r['slot_va']),hx(r['raw']),a.hex(),' '.join(hx(U32(a,k)) for k in range(0,min(20,len(a)-3),4))))

    # semantic grouping by target block
    print('\n[TARGET BLOCK DISTRIBUTION 0x100 GRANULARITY]')
    blocks=collections.Counter((r['raw']-target_lo)//0x100 for r in win)
    for k in sorted(blocks): print('  %s..%s n=%d'%(hx(target_lo+k*0x100),hx(target_lo+(k+1)*0x100-1),blocks[k]))

    # header/table boundary follow-on content
    print('\n[AROUND TABLE BOUNDARY]')
    for lo,hi,name in ((0x00ca7000,0x00ca8000,'before-table'),(0x00ca8000,0x00ca8800,'table'),(0x00ca8800,0x00ca9800,'after-table')):
        so=r2o(pe,lo-ib); eo=r2o(pe,hi-1-ib)
        if so is None or eo is None: print('  %s unmapped'%name); continue
        b=d[so:eo+1]; print('  %-12s entropy=%.4f zero=%d ascii4=%d in_image_dwords=%d'%(
            name,entropy(b),b.count(0),len(runs_ascii(b,4)),sum(ib<=U32(b,k)<ib+pe['soi'] for k in range(0,len(b)-3,4))))

    # Entry chain and sentinel census
    print('\n[ENTRY CHAIN: FF15 -> 0x0E9DC665 -> 0x80000001]')
    eslot_rva=0x0e5dc665; eo=r2o(pe,eslot_rva); esec=sec_of(pe,eslot_rva)
    print('  entry_rva=%s entry_fileoff=%s entry_section=%s#%d'%(
        hx(pe['entry']),hx(r2o(pe,pe['entry'])),sec_of(pe,pe['entry'])['name'],sec_of(pe,pe['entry'])['i']))
    print('  entry bytes=%s'%d[r2o(pe,pe['entry']):r2o(pe,pe['entry'])+16].hex())
    print('  slot_va=%s slot_rva=%s fileoff=%s section=%s#%d value=%s'%(
        hx(0x0e9dc665),hx(eslot_rva),hx(eo),esec['name'],esec['i'],hx(U32(d,eo)) if eo is not None else '-'))
    print('  slot neighborhood:')
    for k in range(-16,17):
        o=eo+k*4
        if 0<=o<=len(d)-4:
            r,s=o2r(pe,o); print('    %+d %s %s section=%s#%d'%(k,hx(ib+r) if r is not None else '-',hx(U32(d,o)),s['name'] if s else '-',s['i'] if s else -1))
    # locate all FF15 instructions whose target slot holds a 0x8xxxxxxx sentinel
    sent=[]
    for x in ev:
        o=r2o(pe,x['slot_rva']) if x['slot_rva']>=0 else None
        if o is not None and o+4<=len(d):
            v=U32(d,o)
            if 0x80000000<=v<=0x8fffffff: sent.append((x,v))
    print('  FF15/FF25 events whose slot holds 0x8xxxxxxx: %d (ff15=%d ff25=%d)'%(
        len(sent),sum(x['opcode']==0x15 for x,v in sent),sum(x['opcode']==0x25 for x,v in sent)))
    for x,v in sent[:100]: print('    caller=%s ins=%s target=%s value=%s'%(hx(x['rva']),hx(x['op']),hx(x['slot_rva']),hx(v)))
    # exact same six bytes census
    pat=bytes.fromhex('FF1565C69D0E'); occ=[]; q=-1
    while True:
        q=d.find(pat,q+1)
        if q<0: break
        r,s=o2r(pe,q); occ.append((q,r,s))
    print('  exact pattern count=%d occurrences=%s'%(len(occ),' '.join(hx(o[0]) for o in occ)))
    # callsites targeting 0x0E9DC665 via any FF15/25
    esrefs=[x for x in ev if x['op']==0x0e9dc665]
    print('  all FF15/25 operands=%s count=%d caller_rvas=%s'%(
        hx(0x0e9dc665),len(esrefs),' '.join(hx(x['rva']) for x in esrefs)))

    # IAT-like caller/target relation graph
    print('\n[SLOT -> TARGET -> CALLER SUMMARY]')
    graph=collections.defaultdict(set)
    for op,v in refs.items():
        j=(op-target_va)//4; r=rows[j]
        graph[(op,r['raw'])].update(x['rva'] for x in v)
    print('edges=%d slots=%d targets=%d callers=%d'%(
        len(graph),len(set(a for a,b in graph)),len(set(b for a,b in graph)),len(set(c for a,b in graph for c in graph[(a,b)]))))
    print('shared targets (same value used by >1 slot):')
    byv=collections.defaultdict(list)
    for r in rows:
        if r['raw'] is not None: byv[r['raw']].append(r)
    for v,rs in sorted(byv.items(),key=lambda kv:-len(kv[1]))[:20]:
        if len(rs)>1: print('  value=%s slots=%s'%(hx(v),' '.join(hx(r['slot_va']) for r in rs)))

    # Entry-stub-like records: 8-byte cells [value,0] with neighboring module name.
    print('\n[ENTRY-STUB / MODULE-DESCRIPTOR CANDIDATE SCAN]')
    seen=[]; q=0
    while q+12<=len(d):
        v=U32(d,q)
        if 0x80000001<=v<=0x8000ffff and U32(d,q+4)==0:
            before=d[max(0,q-24):q]
            atext=''.join(chr(x) if 32<=x<127 else '.' for x in before)
            # module/name immediately after the zero: printable and ends before nonprintable.
            after=d[q+8:]
            stop=0
            while stop<64 and q+8+stop<len(d) and 32<=after[stop]<127: stop+=1
            txt=after[:stop].decode('latin1') if stop>=4 else ''
            r,s=o2r(pe,q) if q<len(d) else (None,None)
            seen.append((q,r,s,v,txt,atext))
        q+=4
    print('cells value+zero=%d sentinel_cells=%d named=%d'%(len(seen),sum(1 for z in seen if z[3]>=0x80000000),sum(1 for z in seen if z[4])))
    for q,r,s,v,txt,before in seen:
        if v>=0x80000000:
            print('  fileoff=%s rva=%s sec=%s val=%s after=%r before=%r'%(hx(q),hx(r) if r is not None else '-',('%s#%d'%(s['name'],s['i'])) if s else '-',hx(v),txt,before[-16:]))
    # CSV
    out=os.path.join(os.path.dirname(os.path.abspath(__file__)),'_out','ca8000_table.csv')
    os.makedirs(os.path.dirname(out),exist_ok=True)
    with open(out,'w',encoding='utf-8',newline='') as f:
        f.write('index,slot_va,slot_rva,slot_file_off,raw_value,value_rva,value_section,target_file_off,ref_count\n')
        for r in rows:
            f.write('%d,0x%08X,0x%08X,%s,0x%08X,%s,%s,%s,%d\n'%(
                r['i'],r['slot_va'],r['slot_rva'],hx(r['slot_off']) if r['slot_off'] is not None else '',
                r['raw'],hx(r['value_rva']) if r['value_rva'] is not None else '',
                ('%s#%d'%(r['target_section']['name'],r['target_section']['i'])) if r['target_section'] else '',
                hx(r['target_off']) if r['target_off'] is not None else '',len(refs.get(r['slot_va'],[]))))
    print('\nCSV=%s'%out)

if __name__=='__main__': main()



